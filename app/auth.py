import os
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt
from dotenv import load_dotenv

load_dotenv()

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 1


class TokenError(Exception):
    pass


def _get_jwt_secret() -> str:
    secret = os.getenv("JWT_SECRET")
    if not secret:
        raise RuntimeError("Missing required environment variable: JWT_SECRET")
    return secret


def hash_password(password: str) -> str:
    if not password:
        raise ValueError("Password cannot be empty")
    salt = bcrypt.gensalt()
    password_hash = bcrypt.hashpw(password.encode("utf-8"), salt)
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
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode = payload.copy()
    to_encode.update({"iat": now, "exp": expires_at})
    return jwt.encode(to_encode, _get_jwt_secret(), algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, _get_jwt_secret(), algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise TokenError("Token has expired") from exc
    except jwt.InvalidTokenError as exc:
        raise TokenError("Invalid authentication token") from exc
