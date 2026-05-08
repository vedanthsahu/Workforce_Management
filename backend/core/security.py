"""Security helpers for authentication and token handling."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import Any
import hashlib
import secrets

import jwt

from backend.core.config import get_settings

ACCESS_TOKEN_COOKIE_NAME = "access_token"
REFRESH_TOKEN_COOKIE_NAME = "refresh_token"
SESSION_TOKEN_COOKIE_NAME = "session_token"

ClaimHook = Callable[[dict[str, Any]], dict[str, Any]]

# Claim hooks are process-global and applied to every access token payload
# created after registration.
CLAIM_HOOKS: list[ClaimHook] = []
ALLOWED_CLAIMS = frozenset(
    {"user_id", "sub", "email", "role", "tenant_id", "session_id", "iat", "exp"}
)


class TokenError(Exception):
    """Base exception for authentication-token validation failures."""

    pass


class ExpiredTokenError(TokenError):
    """Raised when a token is structurally valid but no longer within its TTL."""

    pass


class RefreshTokenReplayError(TokenError):
    """Reserved error type for refresh-token replay detection flows."""

    pass


def register_claim_hook(hook: ClaimHook) -> None:
    """Register a process-wide JWT claim transformation hook.

    Args:
        hook: Callable that receives a copy of the payload and returns a
            transformed claim dictionary.

    Returns:
        None.

    Side Effects:
        Mutates the module-level ``CLAIM_HOOKS`` registry for all subsequent
        token issuances in the current process.

    Failure Modes:
        Raises ``TypeError`` if ``hook`` is not callable.
    """
    if not callable(hook):
        raise TypeError("hook must be callable")
    CLAIM_HOOKS.append(hook)


def build_jwt_payload(
    user: dict[str, Any],
    *,
    extra_claims: dict[str, Any] | None = None,
    claims_hook: ClaimHook | None = None,
) -> dict[str, Any]:
    """Build a validated JWT payload for an authenticated user.

    Args:
        user: User-like mapping containing at least ``user_id`` or ``sub`` and
            ``email``.
        extra_claims: Optional claims to merge into the payload before claim
            filtering.
        claims_hook: Optional per-call claim transformer applied after the
            process-global hooks.

    Returns:
        dict[str, Any]: A validated JWT payload constrained to the configured
        allowed claim set.

    Side Effects:
        Reads cached runtime settings and applies any globally registered claim
        hooks, which makes payload generation process-stateful.

    Failure Modes:
        Raises ``ValueError`` when required identity fields are missing or when
        the final payload fails validation. Raises ``TypeError`` if a claim hook
        returns a non-dictionary payload.
    """
    settings = get_settings()
    subject = str(user.get("user_id") or user.get("sub") or "").strip()
    email = str(user.get("email") or "").strip().lower()
    if not subject:
        raise ValueError("user_id is required to build a JWT payload")

    issued_at = int(datetime.now(timezone.utc).timestamp())
    payload: dict[str, Any] = {
        "user_id": subject,
        "sub": subject,
        "iat": issued_at,
        "exp": issued_at + settings.jwt_access_token_ttl,
    }
    if email:
        payload["email"] = email
    tenant_id = str(user.get("tenant_id") or "").strip()
    if tenant_id:
        payload["tenant_id"] = tenant_id

    if extra_claims:
        payload.update(extra_claims)

    # Apply globally registered hooks first so per-call hooks can override or
    # refine their output when a specific request needs additional control.
    for hook in CLAIM_HOOKS:
        payload = _apply_claim_hook(payload, hook)

    if claims_hook is not None:
        payload = _apply_claim_hook(payload, claims_hook)

    # Strip claims not explicitly allowed by configuration before signing to
    # keep tokens stable and avoid leaking incidental user attributes.
    allowed_claims = set(settings.jwt_allowed_claims) or set(ALLOWED_CLAIMS)
    allowed_claims.update({"user_id", "tenant_id", "iat", "exp"})
    payload = {
        key: value
        for key, value in payload.items()
        if key in allowed_claims and value is not None
    }
    _validate_jwt_payload(payload)
    return payload


def sign_jwt(payload: dict[str, Any]) -> str:
    """Sign a validated JWT payload using the configured secret and algorithm.

    Args:
        payload: JWT claim dictionary to encode.

    Returns:
        str: Encoded JWT string.

    Side Effects:
        Reads cached runtime settings.

    Failure Modes:
        Raises ``ValueError`` if the payload is missing required claims or has
        invalid timestamp values.
    """
    settings = get_settings()
    _validate_jwt_payload(payload)
    return jwt.encode(
        payload,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def decode_token(token: str, *, verify_exp: bool = True) -> dict[str, Any]:
    """Decode and validate a signed JWT.

    Args:
        token: Encoded JWT string.
        verify_exp: Whether expiration should be enforced during decoding.

    Returns:
        dict[str, Any]: Decoded JWT claims.

    Side Effects:
        Reads cached runtime settings.

    Failure Modes:
        Raises ``ExpiredTokenError`` for expired tokens and ``TokenError`` for
        other JWT validation failures.
    """
    if is_microsoft_token(token):
        raise TokenError("Microsoft tokens are not accepted by backend APIs. Use the backend-issued access token.")

    settings = get_settings()
    try:
        return jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            options={"verify_exp": verify_exp},
        )
    except jwt.ExpiredSignatureError as exc:
        raise ExpiredTokenError("Token has expired") from exc
    except jwt.InvalidTokenError as exc:
        raise TokenError("Invalid authentication token") from exc


def is_microsoft_token(token: str) -> bool:
    """Return True when a JWT appears to be issued by Microsoft Entra ID."""
    normalized = str(token or "").strip()
    if not normalized:
        return False

    try:
        payload = jwt.decode(
            normalized,
            options={
                "verify_signature": False,
                "verify_exp": False,
                "verify_aud": False,
            },
        )
    except jwt.InvalidTokenError:
        return False

    issuer = str(payload.get("iss") or "").lower()
    audience = str(payload.get("aud") or "").lower()
    has_microsoft_issuer = "login.microsoftonline.com" in issuer or "sts.windows.net" in issuer
    has_microsoft_identity_claims = bool(payload.get("tid") or payload.get("oid"))
    has_microsoft_graph_audience = audience in {
        "00000003-0000-0000-c000-000000000000",
        "https://graph.microsoft.com",
    }
    return has_microsoft_issuer or (has_microsoft_identity_claims and has_microsoft_graph_audience)


def build_auth_cookie_settings(*, max_age: int) -> dict[str, Any]:
    """Return shared cookie settings for authentication cookies.

    Args:
        max_age: Cookie lifetime in seconds.

    Returns:
        dict[str, Any]: Keyword arguments suitable for FastAPI response cookie
        helpers.

    Side Effects:
        Reads cached runtime settings.

    Failure Modes:
        None. The function only exposes derived configuration values.
    """
    settings = get_settings()
    return {
        "httponly": True,
        "secure": settings.auth_cookie_secure,
        "samesite": settings.auth_cookie_samesite,
        "max_age": max_age,
        "path": "/",
    }


def create_scoped_refresh_token(
    *,
    tenant_id: str,
    user_id: str,
    session_id: str,
) -> dict[str, Any]:
    """Generate a refresh token that carries the tenant and session scope."""
    settings = get_settings()
    token_secret = secrets.token_urlsafe(32)
    token = ".".join((tenant_id, user_id, session_id, token_secret))
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=settings.jwt_refresh_token_ttl)
    return {
        "id": session_id,
        "token": token,
        "token_hash": hash_token(token),
        "expires_at": expires_at,
    }


def hash_token(token: str) -> str:
    """Hash a refresh token for database storage and lookup.

    Args:
        token: Plaintext refresh token supplied by the client.

    Returns:
        str: SHA-256 hex digest of the normalized token value.

    Side Effects:
        None beyond CPU work for hashing.

    Failure Modes:
        Raises ``TokenError`` if the token is empty after trimming.
    """
    normalized = token.strip()
    if not normalized:
        raise TokenError("Refresh token is required")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def parse_refresh_token(token: str) -> dict[str, str]:
    """Extract tenant, user, and session scope from a refresh token."""
    normalized = token.strip()
    if not normalized:
        raise TokenError("Refresh token is required")

    parts = normalized.split(".", 3)
    if len(parts) != 4:
        raise TokenError("Refresh token is invalid")

    tenant_id, user_id, session_id, secret = parts
    if not tenant_id or not user_id or not session_id or not secret:
        raise TokenError("Refresh token is invalid")

    return {
        "tenant_id": tenant_id,
        "user_id": user_id,
        "session_id": session_id,
    }


def _apply_claim_hook(payload: dict[str, Any], hook: ClaimHook) -> dict[str, Any]:
    """Run a claim hook against a defensive copy of the payload.

    Args:
        payload: Current JWT payload.
        hook: Claim transformation callback.

    Returns:
        dict[str, Any]: Transformed payload returned by the hook.

    Side Effects:
        Invokes caller-provided code, which may have its own external effects.

    Failure Modes:
        Raises ``TypeError`` if the hook returns a non-dictionary value.
    """
    transformed = hook(dict(payload))
    if not isinstance(transformed, dict):
        raise TypeError("claim hooks must return a dict")
    return transformed


def _validate_jwt_payload(payload: dict[str, Any]) -> None:
    """Validate the minimum claim contract required by this service.

    Args:
        payload: JWT payload to validate.

    Returns:
        None.

    Side Effects:
        None.

    Failure Modes:
        Raises ``ValueError`` when required claims are missing, empty, or use
        invalid timestamp values.
    """
    required_claims = {"user_id", "tenant_id", "iat", "exp"}
    missing_claims = sorted(claim for claim in required_claims if claim not in payload)
    if missing_claims:
        raise ValueError(f"JWT payload is missing required claims: {', '.join(missing_claims)}")

    if not str(payload["user_id"]).strip():
        raise ValueError("JWT payload claim 'user_id' cannot be empty")
    if not str(payload["tenant_id"]).strip():
        raise ValueError("JWT payload claim 'tenant_id' cannot be empty")
    if "sub" in payload and not str(payload["sub"]).strip():
        raise ValueError("JWT payload claim 'sub' cannot be empty")
    if "email" in payload and not str(payload["email"]).strip():
        raise ValueError("JWT payload claim 'email' cannot be empty")

    try:
        issued_at = int(payload["iat"])
        expires_at = int(payload["exp"])
    except (TypeError, ValueError) as exc:
        raise ValueError("JWT payload claims 'iat' and 'exp' must be integers") from exc

    if expires_at <= issued_at:
        raise ValueError("JWT payload claim 'exp' must be later than 'iat'")
