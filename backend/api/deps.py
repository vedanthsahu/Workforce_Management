from typing import Any, Annotated

import psycopg2
from fastapi import Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from psycopg2.extensions import connection as PGConnection

from backend.core.config import get_settings
from backend.core.security import (
    ACCESS_TOKEN_COOKIE_NAME,
    REFRESH_TOKEN_COOKIE_NAME,
    SESSION_TOKEN_COOKIE_NAME,
    ExpiredTokenError,
    TokenError,
    build_auth_cookie_settings,
    decode_token,
)
from backend.db.connection import get_db
from backend.repositories.user_repository import fetch_user_by_id
from backend.services.auth_service import AuthTokens, refresh_auth_tokens

bearer_scheme = HTTPBearer(auto_error=False)


def get_auth_context(
    request: Request,
    response: Response,
    conn: Annotated[PGConnection, Depends(get_db)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> dict[str, Any]:
    token = request.cookies.get(ACCESS_TOKEN_COOKIE_NAME)
    if token is None and credentials is not None:
        token = credentials.credentials

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "missing_access_token",
                "message": "Access token cookie is missing.",
            },
        )

    try:
        token_payload = decode_token(token)
    except ExpiredTokenError:
        refresh_token = request.cookies.get(REFRESH_TOKEN_COOKIE_NAME)
        if not refresh_token:
            _clear_auth_cookies(response)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "code": "missing_refresh_token",
                    "message": "Refresh token cookie is missing.",
                },
            )

        try:
            auth_tokens = refresh_auth_tokens(conn, refresh_token)
        except HTTPException:
            _clear_auth_cookies(response)
            raise
        _set_auth_cookies(response, auth_tokens)
        token_payload = decode_token(auth_tokens.access_token)
    except TokenError as exc:
        _clear_auth_cookies(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "invalid_access_token",
                "message": str(exc),
            },
        ) from exc

    subject = str(token_payload.get("sub") or "").strip()
    email = str(token_payload.get("email") or "").strip().lower()
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "invalid_access_token",
                "message": "Access token is missing the 'sub' claim.",
            },
        )
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "invalid_access_token",
                "message": "Access token is missing the 'email' claim.",
            },
        )

    claims = {
        "user_id": subject,
        "sub": subject,
        "email": email,
    }

    role = token_payload.get("role")
    if role is not None:
        claims["role"] = str(role)

    tenant = token_payload.get("tenant")
    if tenant is not None:
        claims["tenant"] = str(tenant)

    request.state.auth_claims = claims
    return {
        "claims": claims,
        "token_payload": token_payload,
    }


def get_current_user(
    request: Request,
    auth_context: Annotated[dict[str, Any], Depends(get_auth_context)],
    conn: Annotated[PGConnection, Depends(get_db)],
) -> dict[str, Any]:
    user_id = auth_context["claims"]["user_id"]

    try:
        user = fetch_user_by_id(conn, user_id)
    except psycopg2.Error as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "user_lookup_failed",
                "message": "Failed to load the authenticated user.",
            },
        ) from exc

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "user_not_found",
                "message": "Authenticated user no longer exists.",
            },
        )

    request.state.current_user = user
    return user


def _set_auth_cookies(response: Response, auth_tokens: AuthTokens) -> None:
    response.set_cookie(
        key=ACCESS_TOKEN_COOKIE_NAME,
        value=auth_tokens.access_token,
        **build_auth_cookie_settings(max_age=_access_token_ttl_seconds()),
    )
    response.set_cookie(
        key=REFRESH_TOKEN_COOKIE_NAME,
        value=auth_tokens.refresh_token,
        **build_auth_cookie_settings(max_age=_refresh_token_ttl_seconds()),
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


def _access_token_ttl_seconds() -> int:
    return get_settings().jwt_access_token_ttl


def _refresh_token_ttl_seconds() -> int:
    return get_settings().jwt_refresh_token_ttl
