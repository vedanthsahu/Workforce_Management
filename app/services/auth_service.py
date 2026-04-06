import uuid
from datetime import datetime, timezone
from typing import Any

import psycopg2
from fastapi import HTTPException, status
from psycopg2 import errorcodes
from psycopg2.extensions import connection as PGConnection

from app.core.security import (
    TokenError,
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
    verify_refresh_token,
)
from app.repositories.token_repository import (
    fetch_refresh_token_by_hash,
    revoke_refresh_token,
    revoke_token,
    store_refresh_token,
)
from app.repositories.user_repository import create_user, fetch_user_by_email, fetch_user_by_id
from app.schemas.auth import LoginRequest, MessageResponse, SignupRequest, TokenResponse, UserResponse


def _to_project_id(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Invalid project_id for user",
        ) from exc


def _build_access_token_for_user(user: dict[str, Any]) -> str:
    role = str(user.get("role") or "").strip()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User role is required for token generation",
        )

    return create_access_token(
        user_id=str(user["user_id"]),
        email=str(user["email"]),
        role=role,
        project_id=_to_project_id(user.get("project_id", user.get("project"))),
    )


def signup_user(conn: PGConnection, payload: SignupRequest) -> UserResponse:
    normalized_email = payload.email.strip().lower()
    try:
        existing_user = fetch_user_by_email(conn, normalized_email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )

        created_user = create_user(
            conn,
            user_id=str(uuid.uuid4()),
            name=payload.name.strip(),
            email=normalized_email,
            password_hash=hash_password(payload.password),
            location=payload.location.strip(),
            project=int(payload.project),
            role=payload.role.strip(),
        )
        conn.commit()
    except HTTPException:
        conn.rollback()
        raise
    except psycopg2.Error as exc:
        conn.rollback()
        if exc.pgcode == errorcodes.UNIQUE_VIOLATION:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user",
        ) from exc

    return UserResponse(**created_user)


def login_user(conn: PGConnection, payload: LoginRequest) -> TokenResponse:
    normalized_email = payload.email.strip().lower()
    try:
        user = fetch_user_by_email(conn, normalized_email)
    except psycopg2.Error as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process login",
        ) from exc

    if user is None or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    refresh_data = create_refresh_token(str(user["user_id"]))
    access_token = _build_access_token_for_user(user)

    try:
        store_refresh_token(
            conn,
            token_id=refresh_data["token_id"],
            user_id=str(user["user_id"]),
            token_hash=refresh_data["token_hash"],
            expires_at=refresh_data["expires_at"],
        )
        conn.commit()
    except psycopg2.Error as exc:
        conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to issue tokens",
        ) from exc

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_data["token"],
    )


def refresh_access_token(conn: PGConnection, refresh_token: str) -> TokenResponse:
    try:
        refresh_data = verify_refresh_token(refresh_token)
    except TokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    try:
        token_record = fetch_refresh_token_by_hash(conn, refresh_data["token_hash"])
        if token_record is None or token_record["revoked"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token is invalid or revoked",
            )
        if token_record["token_id"] != refresh_data["token_id"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token is invalid or revoked",
            )

        expires_at = token_record["expires_at"]
        if expires_at is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has expired",
            )
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at <= datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has expired",
            )

        user = fetch_user_by_id(conn, str(token_record["user_id"]))
    except HTTPException:
        raise
    except psycopg2.Error as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to refresh access token",
        ) from exc

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return TokenResponse(access_token=_build_access_token_for_user(user))


def logout_user(
    conn: PGConnection,
    *,
    user_id: str,
    token_jti: str,
    token_expires_at: datetime,
    refresh_token: str,
) -> MessageResponse:
    try:
        refresh_data = verify_refresh_token(refresh_token)
    except TokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    try:
        revoke_token(
            conn,
            jti=token_jti,
            user_id=user_id,
            expires_at=token_expires_at,
        )
        revoked_refresh = revoke_refresh_token(
            conn,
            token_hash=refresh_data["token_hash"],
            user_id=user_id,
        )
        if not revoked_refresh:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token is invalid or already revoked",
            )
        conn.commit()
    except HTTPException:
        conn.rollback()
        raise
    except psycopg2.Error as exc:
        conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to logout",
        ) from exc

    return MessageResponse(message="Logged out successfully")
