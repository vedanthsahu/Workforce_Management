"""HTTP routes for local authentication flows.

This module exposes signup, login, refresh, current-user, and logout endpoints,
and manages the auth cookies written to or cleared from responses.
"""

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
    """Register a new locally authenticated user.

    Args:
        payload: Validated signup request body.
        conn: Request-scoped PostgreSQL connection.

    Returns:
        UserResponse: Created user record.

    Side Effects:
        Delegates to the auth service, which performs database writes and
        transaction management.

    Failure Modes:
        Propagates ``HTTPException`` instances raised by the service layer.
    """
    return signup_user(conn, payload)


@router.post("/auth/login", response_model=MessageResponse)
@router.post("/login", response_model=MessageResponse, include_in_schema=False)
def login(
    payload: LoginRequest,
    response: Response,
    conn: Annotated[PGConnection, Depends(get_db)],
) -> MessageResponse:
    """Authenticate a local user and write auth cookies to the response.

    Args:
        payload: Validated login request body.
        response: Outgoing FastAPI response used to set auth cookies.
        conn: Request-scoped PostgreSQL connection.

    Returns:
        MessageResponse: Confirmation that login succeeded.

    Side Effects:
        Delegates to the auth service for token issuance and mutates the
        response by setting access and refresh token cookies.

    Failure Modes:
        Propagates ``HTTPException`` instances raised by the service layer.
    """
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
    """Rotate the refresh token and replace auth cookies.

    Args:
        request: Incoming FastAPI request used to read the refresh-token cookie.
        response: Outgoing FastAPI response used to replace or clear cookies.
        conn: Request-scoped PostgreSQL connection.

    Returns:
        MessageResponse: Confirmation that the token pair was refreshed.

    Side Effects:
        Reads the refresh-token cookie, may clear auth cookies on failure, and
        sets replacement auth cookies on success.

    Failure Modes:
        Raises ``HTTPException`` when the refresh-token cookie is missing or
        when the service layer rejects the token.
    """
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
    """Return the authenticated user's public profile.

    Args:
        current_user: User record resolved by the authentication dependency.

    Returns:
        UserResponse: Public user profile for the current request.

    Side Effects:
        None. The dependency has already performed any required database work.

    Failure Modes:
        Propagates ``HTTPException`` instances raised while resolving the
        current user dependency.
    """
    return UserResponse(**current_user)


@router.post("/auth/logout", response_model=MessageResponse)
@router.post("/logout", response_model=MessageResponse, include_in_schema=False)
def logout(
    request: Request,
    response: Response,
    conn: Annotated[PGConnection, Depends(get_db)],
) -> MessageResponse:
    """Logout the current user and clear backend-managed cookies.

    Args:
        request: Incoming FastAPI request used to read refresh and session
            cookies.
        response: Outgoing FastAPI response used to clear auth cookies.
        conn: Request-scoped PostgreSQL connection.

    Returns:
        MessageResponse: Stable logout confirmation.

    Side Effects:
        Delegates refresh-token revocation to the auth service, best-effort
        deletes any stored Microsoft Graph session, and clears auth cookies from
        the response.

    Failure Modes:
        Propagates logout failures raised by the auth service. Graph-session
        cleanup failures are intentionally swallowed after rollback.
    """
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
    """Write access and refresh token cookies using route-level TTL settings.

    Args:
        response: Outgoing FastAPI response that will carry the cookies.
        auth_tokens: Token pair to serialize into cookies.

    Returns:
        None.

    Side Effects:
        Mutates the outgoing response by setting HTTP-only auth cookies.

    Failure Modes:
        Propagates response-cookie errors raised by the framework.
    """
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
    """Delete local auth and Graph-session cookies from a response.

    Args:
        response: Outgoing FastAPI response that should clear auth state.

    Returns:
        None.

    Side Effects:
        Mutates the outgoing response by scheduling cookie deletions.

    Failure Modes:
        Propagates response-cookie errors raised by the framework.
    """
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
