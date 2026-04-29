"""HTTP routes for Microsoft SSO and delegated Graph access.

This module implements the browser-facing OAuth redirect flow, user provisioning
from Microsoft identity data, cookie-based storage of SSO session state, and
proxy endpoints that expose selected Microsoft Graph resources to authenticated
clients.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import secrets
from typing import Annotated, Any

import psycopg2
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse, RedirectResponse, Response
from psycopg2.extensions import connection as PGConnection

from backend.api.deps import get_current_user
from backend.core.config import get_settings
from backend.core.security import (
    ACCESS_TOKEN_COOKIE_NAME,
    REFRESH_TOKEN_COOKIE_NAME,
    SESSION_TOKEN_COOKIE_NAME,
    build_auth_cookie_settings,
)
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
from backend.repositories.token_repository import create_session, delete_session, get_session
from backend.repositories.user_repository import upsert_user_from_sso
from backend.services.auth_service import AuthTokens, issue_tokens_for_user

router = APIRouter(tags=["SSO"])

STATE_COOKIE_NAME = "oauth_state"


@router.get("/auth/login", response_model=None)
def auth_login():
    """Start the Microsoft OAuth login flow.

    Returns:
        Response: Redirect response to Microsoft containing a state cookie, or
        an error response if the authorization URL cannot be built.

    Side Effects:
        Generates a CSRF state token, writes it to a short-lived cookie, and
        redirects the client to Microsoft.

    Failure Modes:
        Converts ``SSOError`` raised during URL construction into a structured
        JSON error response.
    """
    try:
        auth_url, state = build_auth_url()
    except SSOError as exc:
        return _error_response(exc.status_code, exc.code, exc.message, exc.details)

    response = RedirectResponse(url=auth_url, status_code=status.HTTP_302_FOUND)
    response.set_cookie(
        key=STATE_COOKIE_NAME,
        value=state,
        **build_auth_cookie_settings(max_age=STATE_TTL_SECONDS),
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
    """Handle the Microsoft OAuth callback and establish local auth state.

    Args:
        request: Incoming FastAPI request used to read the stored state cookie.
        conn: Request-scoped PostgreSQL connection.
        code: Optional authorization code returned by Microsoft.
        state: Optional state parameter returned by Microsoft.
        error: Optional provider error code returned instead of a success code.
        error_description: Optional human-readable provider error description.

    Returns:
        Response: Redirect to the frontend with auth cookies on success, or a
        structured error response on failure.

    Side Effects:
        Validates CSRF state, exchanges the auth code for Microsoft tokens,
        verifies the ID token, reads Microsoft Graph profile data, creates or
        updates the local user, issues backend auth tokens, stores an optional
        Graph session, writes cookies, and commits or rolls back database work.

    Failure Modes:
        Returns structured error responses for provider callback errors, missing
        state or code, failed token exchange, invalid identity data, auth-token
        issuance failures, or database persistence errors.
    """
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
        # Profile enrichment is helpful but not strictly required when Graph
        # denies access to optional fields or returns a missing profile.
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
        auth_tokens = issue_tokens_for_user(conn, user, commit=False)
        conn.commit()
    except HTTPException as exc:
        conn.rollback()
        detail = exc.detail if isinstance(exc.detail, dict) else None
        response = _error_response(exc.status_code, "token_issue_failed", str(exc.detail))
        if detail:
            response = _error_response(
                exc.status_code,
                str(detail.get("code") or "token_issue_failed"),
                str(detail.get("message") or "Failed to issue authentication tokens."),
                {
                    key: value
                    for key, value in detail.items()
                    if key not in {"code", "message"}
                }
                or None,
            )
        _clear_state_cookie(response)
        return response
    except psycopg2.Error:
        conn.rollback()
        response = _error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="sso_persistence_failed",
            message="Failed to create or update the authenticated user.",
        )
        _clear_state_cookie(response)
        return response

    graph_session_token: str | None = None
    try:
        graph_session = create_session(
            conn,
            user_id=str(user["user_id"]),
            email=str(user["email"]),
            access_token=token_payload["access_token"],
        )
        conn.commit()
        graph_session_token = str(graph_session["session_token"])
    except psycopg2.Error:
        # Local authentication should still succeed even if the optional Graph
        # session cannot be persisted for downstream proxy endpoints.
        conn.rollback()

    settings = get_settings()
    response = RedirectResponse(url=settings.frontend_url, status_code=status.HTTP_302_FOUND)
    _set_auth_cookies(response, auth_tokens)
    if graph_session_token:
        response.set_cookie(
            key=SESSION_TOKEN_COOKIE_NAME,
            value=graph_session_token,
            **build_auth_cookie_settings(max_age=settings.session_ttl),
        )
    _clear_state_cookie(response)
    return response


@router.get("/graph/me", response_model=None)
def graph_me(
    request: Request,
    conn: Annotated[PGConnection, Depends(get_db)],
    _: Annotated[dict[str, Any], Depends(get_current_user)],
):
    """Proxy the signed-in user's Microsoft Graph profile.

    Args:
        request: Incoming FastAPI request used to read the Graph session cookie.
        conn: Request-scoped PostgreSQL connection.
        _: Authenticated user dependency used only to enforce local auth.

    Returns:
        dict[str, Any] | JSONResponse: Graph profile payload on success, or a
        structured error response on failure.

    Side Effects:
        Loads the stored Graph access token from the database and performs an
        outbound request to Microsoft Graph.

    Failure Modes:
        Converts ``GraphAPIError`` instances into structured JSON responses.
    """
    try:
        return fetch_graph_me(_require_graph_access_token(conn, request))
    except GraphAPIError as exc:
        return _error_response(exc.status_code, exc.code, exc.message, exc.details)


@router.get("/graph/groups", response_model=None)
def graph_groups(
    request: Request,
    conn: Annotated[PGConnection, Depends(get_db)],
    _: Annotated[dict[str, Any], Depends(get_current_user)],
):
    """Proxy the signed-in user's Microsoft Graph group memberships.

    Args:
        request: Incoming FastAPI request used to read the Graph session cookie.
        conn: Request-scoped PostgreSQL connection.
        _: Authenticated user dependency used only to enforce local auth.

    Returns:
        dict[str, Any] | JSONResponse: Graph group payload on success, or a
        structured error response on failure.

    Side Effects:
        Loads the stored Graph access token from the database and performs an
        outbound request to Microsoft Graph.

    Failure Modes:
        Converts ``GraphAPIError`` instances into structured JSON responses.
    """
    try:
        return fetch_graph_groups(_require_graph_access_token(conn, request))
    except GraphAPIError as exc:
        return _error_response(exc.status_code, exc.code, exc.message, exc.details)


@router.get("/graph/manager", response_model=None)
def graph_manager(
    request: Request,
    conn: Annotated[PGConnection, Depends(get_db)],
    _: Annotated[dict[str, Any], Depends(get_current_user)],
):
    """Proxy the signed-in user's Microsoft Graph manager relationship.

    Args:
        request: Incoming FastAPI request used to read the Graph session cookie.
        conn: Request-scoped PostgreSQL connection.
        _: Authenticated user dependency used only to enforce local auth.

    Returns:
        dict[str, Any] | JSONResponse: Graph manager payload on success, or a
        structured error response on failure.

    Side Effects:
        Loads the stored Graph access token from the database and performs an
        outbound request to Microsoft Graph.

    Failure Modes:
        Converts ``GraphAPIError`` instances into structured JSON responses.
    """
    try:
        return fetch_graph_manager(_require_graph_access_token(conn, request))
    except GraphAPIError as exc:
        return _error_response(exc.status_code, exc.code, exc.message, exc.details)


def _resolve_azure_oid(claims: dict[str, Any], graph_profile: dict[str, Any]) -> str:
    """Resolve the best available Microsoft object identifier for a user.

    Args:
        claims: Verified Microsoft ID token claims.
        graph_profile: Optional Microsoft Graph profile payload.

    Returns:
        str: First non-empty object identifier candidate, or an empty string.

    Side Effects:
        None.

    Failure Modes:
        None. Missing values simply result in an empty string.
    """
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
    """Resolve the best available email address from identity sources.

    Args:
        claims: Verified Microsoft ID token claims.
        graph_profile: Optional Microsoft Graph profile payload.

    Returns:
        str: First non-empty normalized email-like value, or an empty string.

    Side Effects:
        None.

    Failure Modes:
        None. Missing values simply result in an empty string.
    """
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
    """Resolve the best available display name from identity sources.

    Args:
        claims: Verified Microsoft ID token claims.
        graph_profile: Optional Microsoft Graph profile payload.

    Returns:
        str | None: First non-empty display name candidate, otherwise ``None``.

    Side Effects:
        None.

    Failure Modes:
        None.
    """
    for candidate in (
        graph_profile.get("displayName"),
        claims.get("name"),
    ):
        normalized = str(candidate or "").strip()
        if normalized:
            return normalized
    return None


def _require_graph_access_token(conn: PGConnection, request: Request) -> str:
    """Load and validate the stored Microsoft Graph access token for a session.

    Args:
        conn: Request-scoped PostgreSQL connection.
        request: Incoming FastAPI request used to read the session cookie.

    Returns:
        str: Microsoft Graph access token associated with the session.

    Side Effects:
        Reads the stored session from the database, may delete expired sessions,
        and may commit or roll back cleanup work.

    Failure Modes:
        Raises ``GraphAPIError`` when the session cookie is missing, the session
        lookup fails, the session is invalid or expired, or the stored access
        token is absent.
    """
    session_token = request.cookies.get(SESSION_TOKEN_COOKIE_NAME)
    if not session_token:
        raise GraphAPIError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="missing_graph_session",
            message="Microsoft Graph session cookie is missing.",
        )

    try:
        session = get_session(conn, session_token)
    except psycopg2.Error as exc:
        raise GraphAPIError(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="graph_session_lookup_failed",
            message="Failed to load the Microsoft Graph session.",
        ) from exc

    if session is None:
        raise GraphAPIError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="invalid_graph_session",
            message="Microsoft Graph session is invalid.",
        )

    created_at = session["created_at"]
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)

    expires_at = created_at + timedelta(seconds=get_settings().session_ttl)
    if expires_at <= datetime.now(timezone.utc):
        try:
            delete_session(conn, session_token)
            conn.commit()
        except psycopg2.Error:
            conn.rollback()
        raise GraphAPIError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="expired_graph_session",
            message="Microsoft Graph session has expired.",
        )

    access_token = str(session.get("access_token") or "").strip()
    if not access_token:
        raise GraphAPIError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="missing_graph_access_token",
            message="Microsoft Graph access token is missing from the current session.",
        )
    return access_token


def _set_auth_cookies(response: Response, auth_tokens: AuthTokens) -> None:
    """Write backend auth cookies after a successful SSO login.

    Args:
        response: Outgoing FastAPI response that will carry the cookies.
        auth_tokens: Local backend token pair to serialize into cookies.

    Returns:
        None.

    Side Effects:
        Mutates the outgoing response by setting access and refresh token
        cookies.

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


def _clear_state_cookie(response: Response) -> None:
    """Delete the short-lived OAuth state cookie from a response.

    Args:
        response: Outgoing FastAPI response that should clear the state cookie.

    Returns:
        None.

    Side Effects:
        Mutates the outgoing response by scheduling the state cookie deletion.

    Failure Modes:
        Propagates response-cookie errors raised by the framework.
    """
    cookie_settings = build_auth_cookie_settings(max_age=0)
    response.delete_cookie(
        key=STATE_COOKIE_NAME,
        secure=cookie_settings["secure"],
        httponly=True,
        samesite=cookie_settings["samesite"],
        path="/",
    )


def _error_response(
    status_code: int,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> JSONResponse:
    """Build a standardized JSON error response for SSO endpoints.

    Args:
        status_code: HTTP status code to return.
        code: Stable machine-readable error code.
        message: Human-readable error message.
        details: Optional provider or diagnostic details.

    Returns:
        JSONResponse: Response containing the backend's standard ``error``
        envelope.

    Side Effects:
        None beyond creating the response object.

    Failure Modes:
        None expected under normal runtime conditions.
    """
    content: dict[str, Any] = {
        "error": {
            "code": code,
            "message": message,
        }
    }
    if details:
        content["error"]["details"] = details
    return JSONResponse(status_code=status_code, content=content)
