from typing import Any, Annotated

from fastapi import APIRouter, Depends, status
from psycopg2.extensions import connection as PGConnection

from app.api.deps import get_auth_context, get_current_user
from app.db.connection import get_db
from app.schemas.auth import LoginRequest, MessageResponse, SignupRequest, TokenResponse, UserResponse
from app.services.auth_service import login_user, logout_user, signup_user

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


@protected_router.get("/me", response_model=UserResponse)
def me(current_user: Annotated[dict, Depends(get_current_user)]) -> UserResponse:
    return UserResponse(**current_user)


@protected_router.post("/logout", response_model=MessageResponse)
def logout(
    auth_context: Annotated[dict[str, Any], Depends(get_auth_context)],
    conn: Annotated[PGConnection, Depends(get_db)],
) -> MessageResponse:
    return logout_user(
        conn,
        user_id=auth_context["user"]["user_id"],
        token_jti=auth_context["token_jti"],
        token_expires_at=auth_context["token_expires_at"],
    )


router = APIRouter(tags=["auth"])
router.include_router(public_router)
router.include_router(protected_router)
