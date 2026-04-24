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

CLAIM_HOOKS: list[ClaimHook] = []
ALLOWED_CLAIMS = frozenset({"sub", "email", "role", "tenant", "iat", "exp"})


class TokenError(Exception):
    pass


class ExpiredTokenError(TokenError):
    pass


class RefreshTokenReplayError(TokenError):
    pass


def register_claim_hook(hook: ClaimHook) -> None:
    if not callable(hook):
        raise TypeError("hook must be callable")
    CLAIM_HOOKS.append(hook)


def hash_password(password: str) -> str:
    if not password:
        raise ValueError("Password cannot be empty")
    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    return password_hash.decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
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

    for hook in CLAIM_HOOKS:
        payload = _apply_claim_hook(payload, hook)

    if claims_hook is not None:
        payload = _apply_claim_hook(payload, claims_hook)

    allowed_claims = set(settings.jwt_allowed_claims) or set(ALLOWED_CLAIMS)
    payload = {
        key: value
        for key, value in payload.items()
        if key in allowed_claims and value is not None
    }
    _validate_jwt_payload(payload)
    return payload


def sign_jwt(payload: dict[str, Any]) -> str:
    settings = get_settings()
    _validate_jwt_payload(payload)
    return jwt.encode(
        payload,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def decode_token(token: str, *, verify_exp: bool = True) -> dict[str, Any]:
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
    settings = get_settings()
    return {
        "httponly": True,
        "secure": settings.auth_cookie_secure,
        "samesite": settings.auth_cookie_samesite,
        "max_age": max_age,
        "path": "/",
    }


def create_refresh_token() -> dict[str, Any]:
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
    normalized = token.strip()
    if not normalized:
        raise TokenError("Refresh token is required")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _apply_claim_hook(payload: dict[str, Any], hook: ClaimHook) -> dict[str, Any]:
    transformed = hook(dict(payload))
    if not isinstance(transformed, dict):
        raise TypeError("claim hooks must return a dict")
    return transformed


def _validate_jwt_payload(payload: dict[str, Any]) -> None:
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
