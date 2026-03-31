import uuid
from typing import Any, Annotated

import psycopg2
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from psycopg2 import errorcodes
from psycopg2.extras import RealDictCursor
from psycopg2.extensions import connection as PGConnection

from app.auth import TokenError, create_access_token, decode_token, hash_password, verify_password
from app.db import get_db
from app.schemas import LoginRequest, SignupRequest, TokenResponse, UserResponse

router = APIRouter(tags=["auth"])
bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
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

    user_id = token_payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload is missing subject",
        )

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT user_id::text AS user_id, name, email, created_at
                FROM users
                WHERE user_id = %s
                """,
                (user_id,),
            )
            user = cur.fetchone()
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

    return dict(user)


@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def signup(
    payload: SignupRequest,
    conn: Annotated[PGConnection, Depends(get_db)],
) -> UserResponse:
    normalized_email = payload.email.strip().lower()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT 1 FROM users WHERE email = %s",
                (normalized_email,),
            )
            if cur.fetchone():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Email already registered",
                )

            cur.execute(
                """
                INSERT INTO users (user_id, name, email, password_hash)
                VALUES (%s, %s, %s, %s)
                RETURNING user_id::text AS user_id, name, email, created_at
                """,
                (
                    str(uuid.uuid4()),
                    payload.name.strip(),
                    normalized_email,
                    hash_password(payload.password),
                ),
            )
            user = cur.fetchone()
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

    return UserResponse(**dict(user))


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    conn: Annotated[PGConnection, Depends(get_db)],
) -> TokenResponse:
    normalized_email = payload.email.strip().lower()

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT user_id::text AS user_id, email, password_hash
                FROM users
                WHERE email = %s
                """,
                (normalized_email,),
            )
            user = cur.fetchone()
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


@router.get("/me", response_model=UserResponse)
def me(current_user: Annotated[dict[str, Any], Depends(get_current_user)]) -> UserResponse:
    return UserResponse(**current_user)
