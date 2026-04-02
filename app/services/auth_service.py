import uuid
from datetime import datetime

import psycopg2
from fastapi import HTTPException, status
from psycopg2 import errorcodes
from psycopg2.extensions import connection as PGConnection

from app.core.security import create_access_token, hash_password, verify_password
from app.repositories.token_repository import revoke_token
from app.repositories.user_repository import create_user, fetch_user_by_email
from app.schemas.auth import LoginRequest, MessageResponse, SignupRequest, TokenResponse, UserResponse


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
            project=payload.project.strip(),
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

    access_token = create_access_token(
        {"sub": user["user_id"], "email": user["email"]},
    )
    return TokenResponse(access_token=access_token)


def logout_user(
    conn: PGConnection,
    *,
    user_id: str,
    token_jti: str,
    token_expires_at: datetime,
) -> MessageResponse:
    try:
        revoke_token(
            conn,
            jti=token_jti,
            user_id=user_id,
            expires_at=token_expires_at,
        )
        conn.commit()
    except psycopg2.Error as exc:
        conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to logout",
        ) from exc

    return MessageResponse(message="Logged out successfully")
