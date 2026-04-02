from datetime import datetime, timedelta, timezone
from typing import Any
import uuid

import bcrypt
import jwt

from app.core.config import get_settings


class TokenError(Exception):
    pass


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


def create_access_token(payload: dict[str, Any]) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=settings.jwt_expire_hours)
    token_payload = payload.copy()
    token_payload.update(
        {
            "iat": now,
            "exp": expires_at,
            "jti": token_payload.get("jti", str(uuid.uuid4())),
        }
    )
    return jwt.encode(
        token_payload,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


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
