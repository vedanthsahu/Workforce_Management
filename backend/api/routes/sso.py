from __future__ import annotations

import secrets
from typing import Annotated, Any

import psycopg2
from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse, RedirectResponse, Response
from psycopg2.extensions import connection as PGConnection

from backend.api.deps import get_current_user
from backend.core.config import get_settings
from backend.core.sso import (
    GraphAPIError,
    SSOError,
    STATE_TTL_SECONDS,
    build_auth_url,
    exchange_code_for_token,
    fetch_graph_groups,
    fetch_graph_manager,
    fetch_graph_me,
    verify_id_token,
)
from backend.db.connection import get_db
from backend.repositories.token_repository import create_session, delete_session
from backend.repositories.user_repository import upsert_user_from_sso

router = APIRouter(tags=["SSO"])

SESSION_COOKIE_NAME = "session_token"
STATE_COOKIE_NAME = "oauth_state"


@router.get("/auth/login", response_model=None)
def auth_login():
    try:
        auth_url, state = build_auth_url()
    except SSOError as exc:
        return _error_response(exc.status_code, exc.code, exc.message, exc.details)

    response = RedirectResponse(url=auth_url, status_code=status.HTTP_302_FOUND)
    response.set_cookie(
        key=STATE_COOKIE_NAME,
        value=state,
        max_age=STATE_TTL_SECONDS,
        **_cookie_settings(),
    )
    return response


@router.get("/auth/callback", response_model=None)
def auth_callback(
    request: Request,
    conn: Annotated[PGConnection, Depends(get_db)],
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
):
    if error:
        response = _error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="microsoft_auth_error",
            message="Microsoft returned an authentication error.",
            details={
                "provider_error": error,
                "provider_message": error_description or "Unknown Microsoft authentication error.",
            },
        )
        _clear_state_cookie(response)
        return response

    if not code:
        response = _error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="missing_authorization_code",
            message="Microsoft callback did not include an authorization code.",
        )
        _clear_state_cookie(response)
        return response

    if not state:
        response = _error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="missing_state",
            message="Microsoft callback did not include a state parameter.",
        )
        _clear_state_cookie(response)
        return response

    state_cookie = request.cookies.get(STATE_COOKIE_NAME)
    if not state_cookie or not secrets.compare_digest(state_cookie, state):
        response = _error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="invalid_state",
            message="Microsoft login state is invalid or has expired.",
        )
        _clear_state_cookie(response)
        return response

    try:
        token_payload = exchange_code_for_token(code)
        claims = verify_id_token(token_payload["id_token"])
    except SSOError as exc:
        response = _error_response(exc.status_code, exc.code, exc.message, exc.details)
        _clear_state_cookie(response)
        return response

    graph_profile: dict[str, Any] = {}
    try:
        graph_profile = fetch_graph_me(token_payload["access_token"])
    except GraphAPIError as exc:
        if exc.status_code not in {status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND}:
            response = _error_response(exc.status_code, exc.code, exc.message, exc.details)
            _clear_state_cookie(response)
            return response

    azure_oid = _resolve_azure_oid(claims, graph_profile)
    email = _resolve_email(claims, graph_profile)
    display_name = _resolve_display_name(claims, graph_profile)

    if not azure_oid:
        response = _error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="missing_oid",
            message="Microsoft identity claims did not include an object identifier.",
        )
        _clear_state_cookie(response)
        return response

    if not email:
        response = _error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="missing_email",
            message="Microsoft identity claims did not include a usable email address.",
        )
        _clear_state_cookie(response)
        return response

    try:
        user = upsert_user_from_sso(
            conn,
            azure_oid=azure_oid,
            email=email,
            display_name=display_name,
        )
        session = create_session(
            conn,
            user_id=str(user["user_id"]),
            email=str(user["email"]),
            access_token=token_payload["access_token"],
        )
        conn.commit()
    except psycopg2.Error:
        conn.rollback()
        response = _error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="session_persistence_failed",
            message="Failed to persist the authenticated SSO session.",
        )
        _clear_state_cookie(response)
        return response

    settings = get_settings()
    response = RedirectResponse(url=settings.frontend_url, status_code=status.HTTP_302_FOUND)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session["session_token"],
        max_age=settings.session_ttl,
        **_cookie_settings(),
    )
    _clear_state_cookie(response)
    return response


@router.get("/auth/me")
def auth_me(
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
) -> dict[str, Any]:
    return current_user


@router.get("/auth/logout", response_model=None)
def auth_logout(
    request: Request,
    conn: Annotated[PGConnection, Depends(get_db)],
):
    session_token = request.cookies.get(SESSION_COOKIE_NAME)
    if session_token:
        try:
            delete_session(conn, session_token)
            conn.commit()
        except psycopg2.Error:
            conn.rollback()
            response = _error_response(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                code="session_delete_failed",
                message="Failed to delete the current session.",
            )
            _clear_session_cookie(response)
            _clear_state_cookie(response)
            return response

    response = RedirectResponse(url=get_settings().frontend_url, status_code=status.HTTP_302_FOUND)
    _clear_session_cookie(response)
    _clear_state_cookie(response)
    return response


@router.get("/graph/me", response_model=None)
def graph_me(
    request: Request,
    _: Annotated[dict[str, Any], Depends(get_current_user)],
):
    try:
        return fetch_graph_me(_require_access_token(request))
    except GraphAPIError as exc:
        return _error_response(exc.status_code, exc.code, exc.message, exc.details)


@router.get("/graph/groups", response_model=None)
def graph_groups(
    request: Request,
    _: Annotated[dict[str, Any], Depends(get_current_user)],
):
    try:
        return fetch_graph_groups(_require_access_token(request))
    except GraphAPIError as exc:
        return _error_response(exc.status_code, exc.code, exc.message, exc.details)


@router.get("/graph/manager", response_model=None)
def graph_manager(
    request: Request,
    _: Annotated[dict[str, Any], Depends(get_current_user)],
):
    try:
        return fetch_graph_manager(_require_access_token(request))
    except GraphAPIError as exc:
        return _error_response(exc.status_code, exc.code, exc.message, exc.details)


def _resolve_azure_oid(claims: dict[str, Any], graph_profile: dict[str, Any]) -> str:
    for candidate in (
        claims.get("oid"),
        claims.get("sub"),
        graph_profile.get("id"),
    ):
        normalized = str(candidate or "").strip()
        if normalized:
            return normalized
    return ""


def _resolve_email(claims: dict[str, Any], graph_profile: dict[str, Any]) -> str:
    for candidate in (
        claims.get("preferred_username"),
        claims.get("email"),
        graph_profile.get("mail"),
        graph_profile.get("userPrincipalName"),
    ):
        normalized = str(candidate or "").strip().lower()
        if normalized:
            return normalized
    return ""


def _resolve_display_name(claims: dict[str, Any], graph_profile: dict[str, Any]) -> str | None:
    for candidate in (
        graph_profile.get("displayName"),
        claims.get("name"),
    ):
        normalized = str(candidate or "").strip()
        if normalized:
            return normalized
    return None


def _require_access_token(request: Request) -> str:
    session = getattr(request.state, "session", None)
    access_token = None if session is None else session.get("access_token")
    if not access_token:
        raise GraphAPIError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="missing_access_token",
            message="The current session does not include a Microsoft access token.",
        )
    return str(access_token)


def _cookie_settings() -> dict[str, Any]:
    return {
        "httponly": True,
        "secure": True,
        "samesite": "none",
        "path": "/",
    }


def _clear_state_cookie(response: Response) -> None:
    response.delete_cookie(
        key=STATE_COOKIE_NAME,
        secure=True,
        httponly=True,
        samesite="none",
        path="/",
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        secure=True,
        httponly=True,
        samesite="none",
        path="/",
    )


def _error_response(
    status_code: int,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> JSONResponse:
    content: dict[str, Any] = {
        "error": {
            "code": code,
            "message": message,
        }
    }
    if details:
        content["error"]["details"] = details
    return JSONResponse(status_code=status_code, content=content)