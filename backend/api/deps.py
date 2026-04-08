from typing import Any, Annotated
from datetime import datetime, timezone

import psycopg2
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from psycopg2.extensions import connection as PGConnection

from backend.core.security import TokenError, decode_token
from backend.db.connection import get_db
from backend.repositories.token_repository import is_token_revoked
from backend.repositories.user_repository import fetch_user_by_id

bearer_scheme = HTTPBearer(auto_error=False)


def _parse_exp_claim(exp_claim: Any) -> datetime:
    if isinstance(exp_claim, datetime):
        return exp_claim.astimezone(timezone.utc) if exp_claim.tzinfo else exp_claim.replace(tzinfo=timezone.utc)
    if isinstance(exp_claim, (int, float)):
        return datetime.fromtimestamp(exp_claim, tz=timezone.utc)
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token payload has invalid expiration claim",
    )


def get_auth_context(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    conn: Annotated[PGConnection, Depends(get_db)],
) -> dict[str, Any]:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )

    try:
        token_payload = decode_token(credentials.credentials)
    except TokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    user_id = token_payload.get("user_id")
    email = token_payload.get("email")
    role = token_payload.get("role")
    project_id = token_payload.get("project_id")
    token_jti = token_payload.get("jti")
    token_exp = token_payload.get("exp")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload is missing user_id",
        )
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload is missing email",
        )
    if not role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload is missing role",
        )
    if project_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload is missing project_id",
        )
    if not token_jti:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload is missing jti",
        )

    expires_at = _parse_exp_claim(token_exp)

    try:
        if is_token_revoked(conn, token_jti):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
            )
        user = fetch_user_by_id(conn, user_id)
    except psycopg2.Error as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch user profile",
        ) from exc

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found for token",
        )

    try:
        normalized_project_id = int(project_id)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload has invalid project_id",
        ) from exc

    return {
        "user": user,
        "claims": {
            "user_id": str(user_id),
            "email": str(email),
            "role": str(role),
            "project_id": normalized_project_id,
        },
        "token_jti": token_jti,
        "token_expires_at": expires_at,
        "token_payload": token_payload,
    }


def get_current_user(
    auth_context: Annotated[dict[str, Any], Depends(get_auth_context)],
) -> dict[str, Any]:
    return auth_context["user"]
