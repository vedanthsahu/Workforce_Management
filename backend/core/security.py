from datetime import datetime, timedelta, timezone
from typing import Any
import hashlib
import secrets
import uuid

import bcrypt
import jwt

from backend.core.config import get_settings


class TokenError(Exception):
    pass


REFRESH_TOKEN_EXPIRE_DAYS = 30


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


def create_access_token(
    *,
    user_id: str,
    email: str,
    role: str,
    project_id: int,
    jti: str | None = None,
) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=settings.jwt_expire_hours)
    token_payload = {
        "user_id": user_id,
        "email": email,
        "role": role,
        "project_id": project_id,
        "iat": now,
        "exp": expires_at,
        "jti": jti or str(uuid.uuid4()),
    }
    return jwt.encode(
        token_payload,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def _hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_refresh_token(user_id: str) -> dict[str, Any]:
    if not user_id:
        raise ValueError("user_id is required for refresh token generation")

    token_id = str(uuid.uuid4())
    random_segment = secrets.token_urlsafe(48)
    refresh_token = f"{token_id}.{random_segment}"
    expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    return {
        "token": refresh_token,
        "token_id": token_id,
        "user_id": user_id,
        "token_hash": _hash_refresh_token(refresh_token),
        "expires_at": expires_at,
    }


def verify_refresh_token(token: str) -> dict[str, str]:
    if not token:
        raise TokenError("Refresh token is required")

    parts = token.split(".", 1)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise TokenError("Invalid refresh token")

    token_id, _ = parts
    try:
        uuid.UUID(token_id)
    except ValueError as exc:
        raise TokenError("Invalid refresh token") from exc

    return {
        "token_id": token_id,
        "token_hash": _hash_refresh_token(token),
    }


def decode_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        return jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.ExpiredSignatureError as exc:
        raise TokenError("Token has expired") from exc
    except jwt.InvalidTokenError as exc:
        raise TokenError("Invalid authentication token") from exc
