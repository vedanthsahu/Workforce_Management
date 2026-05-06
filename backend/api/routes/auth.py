"""HTTP routes for SSO-issued backend authentication tokens."""

from __future__ import annotations

from typing import Any, Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from psycopg2.extensions import connection as PGConnection
from backend.services.auth_service import logout_user_session
from backend.api.deps import get_current_user
from backend.core.config import get_settings
from backend.core.security import (
    ACCESS_TOKEN_COOKIE_NAME,
    REFRESH_TOKEN_COOKIE_NAME,
    SESSION_TOKEN_COOKIE_NAME,
    build_auth_cookie_settings,
)
from backend.db.connection import get_db
from backend.schemas.auth import MessageResponse, UserResponse
from backend.services.auth_service import AuthTokens, refresh_auth_tokens

router = APIRouter(tags=["auth"])

@router.post("/auth/logout", response_model=MessageResponse)
def logout(
    request: Request,
    response: Response,
    conn: Annotated[PGConnection, Depends(get_db)],
) -> MessageResponse:
    refresh_token = request.cookies.get(REFRESH_TOKEN_COOKIE_NAME)

    if refresh_token:
        logout_user_session(conn, refresh_token)

    _clear_auth_cookies(response)

    return MessageResponse(message="Logged out successfully")
@router.post("/auth/refresh", response_model=MessageResponse)
def refresh_token(
    request: Request,
    response: Response,
    conn: Annotated[PGConnection, Depends(get_db)],
) -> MessageResponse:
    """Rotate SSO-issued backend auth tokens from the refresh cookie."""
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

    auth_tokens = refresh_auth_tokens(
        conn,
        refresh_token_cookie,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )
    _set_auth_cookies(response, auth_tokens)
    return MessageResponse(message="Token refreshed")


@router.get("/auth/me", response_model=UserResponse)
def me(current_user: Annotated[dict[str, Any], Depends(get_current_user)]) -> UserResponse:
    """Return the user represented by the backend access token."""
    return UserResponse(**current_user)


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
