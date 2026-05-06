"""Shared FastAPI dependencies for authenticated routes."""

from __future__ import annotations

from typing import Any, Annotated

import psycopg2
from fastapi import Depends, HTTPException, Request, Response, status
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
    is_microsoft_token,
)
from backend.db.connection import get_db
from backend.repositories.user_repository import fetch_user_by_id
from backend.services.auth_service import AuthTokens, refresh_auth_tokens


def get_auth_context(
    request: Request,
    response: Response,
    conn: Annotated[PGConnection, Depends(get_db)],
) -> dict[str, Any]:
    """Resolve authenticated claims from a backend-issued access token."""
    bearer_token = _extract_bearer_token(request)
    if bearer_token and is_microsoft_token(bearer_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "microsoft_token_not_accepted",
                "message": "Microsoft access tokens are not accepted by backend APIs. Use the backend-issued access token.",
            },
        )

    token = request.cookies.get(ACCESS_TOKEN_COOKIE_NAME) or bearer_token

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "missing_access_token",
                "message": "Access token is missing.",
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
            auth_tokens = refresh_auth_tokens(
                conn,
                refresh_token,
                user_agent=request.headers.get("user-agent"),
                ip_address=request.client.host if request.client else None,
            )
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

    claims = _parse_auth_claims(token_payload)
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
    """Load the current authenticated user record from the database."""
    tenant_id = auth_context["claims"]["tenant_id"]
    user_id = auth_context["claims"]["user_id"]

    try:
        user = fetch_user_by_id(conn, tenant_id=tenant_id, user_id=user_id)
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


def _parse_auth_claims(token_payload: dict[str, Any]) -> dict[str, Any]:
    subject = str(token_payload.get("user_id") or token_payload.get("sub") or "").strip()
    email = str(token_payload.get("email") or "").strip().lower()
    tenant_id = str(token_payload.get("tenant_id") or "").strip()
    session_id = str(token_payload.get("session_id") or "").strip()

    if not subject:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "invalid_access_token",
                "message": "Access token is missing the 'user_id' claim.",
            },
        )
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "invalid_access_token",
                "message": "Access token is missing the 'tenant_id' claim.",
            },
        )

    claims = {
        "user_id": subject,
        "sub": subject,
        "tenant_id": tenant_id,
    }
    if email:
        claims["email"] = email
    if session_id:
        claims["session_id"] = session_id

    role = token_payload.get("role")
    if role is not None:
        claims["role"] = str(role)

    return claims


def _extract_bearer_token(request: Request) -> str | None:
    authorization = str(request.headers.get("authorization") or "").strip()
    if not authorization:
        return None

    scheme, _, credentials = authorization.partition(" ")
    if scheme.lower() != "bearer" or not credentials.strip():
        return None
    return credentials.strip()


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
