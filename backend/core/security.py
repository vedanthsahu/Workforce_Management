"""Security helpers for local authentication and token handling.

This module owns password hashing, JWT payload construction and validation,
HTTP cookie defaults for auth tokens, refresh-token generation, and the
process-global registry of claim hooks used to augment JWT claims.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import Any
import hashlib
import secrets
import uuid

import bcrypt
import jwt

from backend.core.config import get_settings

ACCESS_TOKEN_COOKIE_NAME = "access_token"
REFRESH_TOKEN_COOKIE_NAME = "refresh_token"
SESSION_TOKEN_COOKIE_NAME = "session_token"

ClaimHook = Callable[[dict[str, Any]], dict[str, Any]]

# Claim hooks are process-global and applied to every access token payload
# created after registration.
CLAIM_HOOKS: list[ClaimHook] = []
ALLOWED_CLAIMS = frozenset({"sub", "email", "role", "tenant", "iat", "exp"})


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


def hash_password(password: str) -> str:
    """Hash a plaintext password for storage.

    Args:
        password: User-supplied plaintext password. It must be non-empty.

    Returns:
        str: A bcrypt password hash encoded as UTF-8 text.

    Side Effects:
        Performs CPU-intensive bcrypt hashing.

    Failure Modes:
        Raises ``ValueError`` if the password is empty.
    """
    if not password:
        raise ValueError("Password cannot be empty")
    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    return password_hash.decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Check whether a plaintext password matches a stored bcrypt hash.

    Args:
        password: Plaintext password to verify.
        password_hash: Stored bcrypt hash as text.

    Returns:
        bool: ``True`` when the password matches the stored hash.

    Side Effects:
        Performs bcrypt verification work.

    Failure Modes:
        Returns ``False`` for missing inputs or malformed hash values instead of
        propagating bcrypt parsing errors.
    """
    if not password or not password_hash:
        return False
    try:
        return bcrypt.checkpw(
            password.encode("utf-8"),
            password_hash.encode("utf-8"),
        )
    except ValueError:
        return False


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
    if not email:
        raise ValueError("email is required to build a JWT payload")

    issued_at = int(datetime.now(timezone.utc).timestamp())
    payload: dict[str, Any] = {
        "sub": subject,
        "email": email,
        "iat": issued_at,
        "exp": issued_at + settings.jwt_access_token_ttl,
    }

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


def create_refresh_token() -> dict[str, Any]:
    """Generate a refresh token and its persistent metadata.

    Returns:
        dict[str, Any]: Token identifier, plaintext token, token hash, and
        expiration timestamp.

    Side Effects:
        Uses cryptographically secure randomness and reads cached JWT TTL
        configuration.

    Failure Modes:
        None expected under normal runtime conditions.
    """
    settings = get_settings()
    token = secrets.token_urlsafe(32)
    token_id = str(uuid.uuid4())
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=settings.jwt_refresh_token_ttl)
    return {
        "id": token_id,
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
    required_claims = {"sub", "email", "iat", "exp"}
    missing_claims = sorted(claim for claim in required_claims if claim not in payload)
    if missing_claims:
        raise ValueError(f"JWT payload is missing required claims: {', '.join(missing_claims)}")

    if not str(payload["sub"]).strip():
        raise ValueError("JWT payload claim 'sub' cannot be empty")
    if not str(payload["email"]).strip():
        raise ValueError("JWT payload claim 'email' cannot be empty")

    try:
        issued_at = int(payload["iat"])
        expires_at = int(payload["exp"])
    except (TypeError, ValueError) as exc:
        raise ValueError("JWT payload claims 'iat' and 'exp' must be integers") from exc

    if expires_at <= issued_at:
        raise ValueError("JWT payload claim 'exp' must be later than 'iat'")
