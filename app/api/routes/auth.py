from typing import Any, Annotated

from fastapi import APIRouter, Depends, status
from psycopg2.extensions import connection as PGConnection

from app.api.deps import get_auth_context, get_current_user
from app.db.connection import get_db
from app.schemas.auth import (
    LoginRequest,
    LogoutRequest,
    MessageResponse,
    RefreshTokenRequest,
    SignupRequest,
    TokenResponse,
    UserResponse,
)
from app.services.auth_service import login_user, logout_user, refresh_access_token, signup_user

public_router = APIRouter(tags=["auth"])
protected_router = APIRouter(tags=["auth"], dependencies=[Depends(get_auth_context)])


@public_router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def signup(
    payload: SignupRequest,
    conn: Annotated[PGConnection, Depends(get_db)],
) -> UserResponse:
    return signup_user(conn, payload)


@public_router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    conn: Annotated[PGConnection, Depends(get_db)],
) -> TokenResponse:
    return login_user(conn, payload)


@public_router.post("/refresh", response_model=TokenResponse)
def refresh_token(
    payload: RefreshTokenRequest,
    conn: Annotated[PGConnection, Depends(get_db)],
) -> TokenResponse:
    return refresh_access_token(conn, payload.refresh_token)


@protected_router.get("/me", response_model=UserResponse)
def me(current_user: Annotated[dict, Depends(get_current_user)]) -> UserResponse:
    return UserResponse(**current_user)


@protected_router.post("/logout", response_model=MessageResponse)
def logout(
    payload: LogoutRequest,
    auth_context: Annotated[dict[str, Any], Depends(get_auth_context)],
    conn: Annotated[PGConnection, Depends(get_db)],
) -> MessageResponse:
    return logout_user(
        conn,
        user_id=auth_context["claims"]["user_id"],
        token_jti=auth_context["token_jti"],
        token_expires_at=auth_context["token_expires_at"],
        refresh_token=payload.refresh_token,
    )


router = APIRouter(tags=["auth"])
router.include_router(public_router)
router.include_router(protected_router)
