from typing import Any, Annotated

import psycopg2
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from psycopg2.extensions import connection as PGConnection

from backend.api.deps import get_current_user
from backend.core.config import get_settings
from backend.core.security import (
    ACCESS_TOKEN_COOKIE_NAME,
    REFRESH_TOKEN_COOKIE_NAME,
    SESSION_TOKEN_COOKIE_NAME,
    build_auth_cookie_settings,
)
from backend.db.connection import get_db
from backend.repositories.token_repository import delete_session
from backend.schemas.auth import LoginRequest, MessageResponse, SignupRequest, UserResponse
from backend.services.auth_service import AuthTokens, login_user, logout_user, refresh_auth_tokens, signup_user

router = APIRouter(tags=["auth"])


@router.post("/auth/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
def signup(
    payload: SignupRequest,
    conn: Annotated[PGConnection, Depends(get_db)],
) -> UserResponse:
    return signup_user(conn, payload)


@router.post("/auth/login", response_model=MessageResponse)
@router.post("/login", response_model=MessageResponse, include_in_schema=False)
def login(
    payload: LoginRequest,
    response: Response,
    conn: Annotated[PGConnection, Depends(get_db)],
) -> MessageResponse:
    auth_tokens = login_user(conn, payload)
    _set_auth_cookies(response, auth_tokens)
    return MessageResponse(message="Login successful")


@router.post("/auth/refresh", response_model=MessageResponse)
@router.post("/refresh", response_model=MessageResponse, include_in_schema=False)
def refresh_token(
    request: Request,
    response: Response,
    conn: Annotated[PGConnection, Depends(get_db)],
) -> MessageResponse:
    refresh_token_cookie = request.cookies.get(REFRESH_TOKEN_COOKIE_NAME)
    if not refresh_token_cookie:
        _clear_auth_cookies(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "missing_refresh_token",
                "message": "Refresh token cookie is missing.",
            },
        )

    auth_tokens = refresh_auth_tokens(conn, refresh_token_cookie)
    _set_auth_cookies(response, auth_tokens)
    return MessageResponse(message="Token refreshed")


@router.get("/auth/me", response_model=UserResponse)
@router.get("/me", response_model=UserResponse, include_in_schema=False)
def me(current_user: Annotated[dict[str, Any], Depends(get_current_user)]) -> UserResponse:
    return UserResponse(**current_user)


@router.post("/auth/logout", response_model=MessageResponse)
@router.post("/logout", response_model=MessageResponse, include_in_schema=False)
def logout(
    request: Request,
    response: Response,
    conn: Annotated[PGConnection, Depends(get_db)],
) -> MessageResponse:
    message = logout_user(
        conn,
        refresh_token=request.cookies.get(REFRESH_TOKEN_COOKIE_NAME),
    )

    session_token = request.cookies.get(SESSION_TOKEN_COOKIE_NAME)
    if session_token:
        try:
            delete_session(conn, session_token)
            conn.commit()
        except psycopg2.Error:
            conn.rollback()

    _clear_auth_cookies(response)
    return message


def _set_auth_cookies(response: Response, auth_tokens: AuthTokens) -> None:
    settings = get_settings()
    response.set_cookie(
        key=ACCESS_TOKEN_COOKIE_NAME,
        value=auth_tokens.access_token,
        **build_auth_cookie_settings(max_age=settings.jwt_access_token_ttl),
    )
    response.set_cookie(
        key=REFRESH_TOKEN_COOKIE_NAME,
        value=auth_tokens.refresh_token,
        **build_auth_cookie_settings(max_age=settings.jwt_refresh_token_ttl),
    )


def _clear_auth_cookies(response: Response) -> None:
    cookie_settings = build_auth_cookie_settings(max_age=0)
    response.delete_cookie(
        key=ACCESS_TOKEN_COOKIE_NAME,
        secure=cookie_settings["secure"],
        httponly=True,
        samesite=cookie_settings["samesite"],
        path="/",
    )
    response.delete_cookie(
        key=REFRESH_TOKEN_COOKIE_NAME,
        secure=cookie_settings["secure"],
        httponly=True,
        samesite=cookie_settings["samesite"],
        path="/",
    )
    response.delete_cookie(
        key=SESSION_TOKEN_COOKIE_NAME,
        secure=cookie_settings["secure"],
        httponly=True,
        samesite=cookie_settings["samesite"],
        path="/",
    )
