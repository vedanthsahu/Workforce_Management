"""HTTP routes for Microsoft SSO and delegated Graph access."""

from __future__ import annotations

import secrets
from typing import Annotated, Any, Callable

import psycopg2
from fastapi import APIRouter, Depends, Request, status
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
from backend.repositories.user_repository import (
    create_app_user_from_graph,
    create_auth_identity_for_user,
    fetch_active_tenant_for_login,
    fetch_user_by_id,
    fetch_user_by_microsoft_object_id,
    sync_graph_groups_for_user,
    upsert_user_graph_profile,
)
from backend.services.auth_service import AuthTokens, issue_tokens_for_user

router = APIRouter(tags=["SSO"])

STATE_COOKIE_NAME = "oauth_state"
MICROSOFT_PROVIDER = "MICROSOFT"


@router.get("/auth/login", response_model=None)
def auth_login():
    """Start the Microsoft OAuth login flow."""
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
    """Handle Microsoft OAuth callback and establish local auth state."""
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

    azure_tenant_id = str(claims.get("tid") or "").strip()
    if not azure_tenant_id:
        response = _error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="missing_tenant_claim",
            message="Microsoft identity claims did not include a tenant id.",
        )
        _clear_state_cookie(response)
        return response

    try:
        tenant = fetch_active_tenant_for_login(conn, azure_tenant_id=azure_tenant_id)
        if tenant is None:
            response = _error_response(
                status_code=status.HTTP_401_UNAUTHORIZED,
                code="unknown_tenant",
                message="No active application tenant is available for the Microsoft tenant.",
            )
            _clear_state_cookie(response)
            return response
    except LookupError as exc:
        response = _error_response(
            status_code=status.HTTP_409_CONFLICT,
            code="tenant_resolution_ambiguous",
            message=str(exc),
        )
        _clear_state_cookie(response)
        return response
    except psycopg2.Error:
        response = _error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="tenant_resolution_failed",
            message="Failed to resolve the local application tenant.",
        )
        _clear_state_cookie(response)
        return response

    tenant_id = str(tenant["tenant_id"])
    microsoft_object_id = _resolve_claim_object_id(claims)

    try:
        graph_profile: dict[str, Any] = {}
        user = None
        if microsoft_object_id:
            user = fetch_user_by_microsoft_object_id(
                conn,
                tenant_id=tenant_id,
                microsoft_object_id=microsoft_object_id,
            )

        if user is None:
            graph_profile = _fetch_graph_payload(fetch_graph_me, token_payload["access_token"], required=True)
            graph_object_id = _resolve_graph_object_id(graph_profile)
            if microsoft_object_id and graph_object_id != microsoft_object_id:
                raise ValueError("Microsoft ID token oid did not match Graph /me id.")
            microsoft_object_id = graph_object_id

            user = fetch_user_by_microsoft_object_id(
                conn,
                tenant_id=tenant_id,
                microsoft_object_id=microsoft_object_id,
            )

        if user is None:
            graph_manager = _fetch_graph_payload(fetch_graph_manager, token_payload["access_token"], required=False)
            graph_groups = _fetch_graph_payload(fetch_graph_groups, token_payload["access_token"], required=True)
            user = _provision_first_time_user(
                conn,
                tenant_id=tenant_id,
                azure_tenant_id=azure_tenant_id,
                microsoft_object_id=microsoft_object_id,
                claims=claims,
                graph_profile=graph_profile,
                graph_manager=graph_manager,
                graph_groups=graph_groups,
            )

        if user is None:
            raise LookupError("SSO user could not be resolved after provisioning.")
        if user.get("status") != "ACTIVE":
            raise PermissionError("Authenticated user is not ACTIVE.")

        auth_tokens = issue_tokens_for_user(
            conn,
            user,
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host if request.client else None,
            commit=False,
        )
        conn.commit()
    except PermissionError as exc:
        conn.rollback()
        response = _error_response(
            status_code=status.HTTP_403_FORBIDDEN,
            code="inactive_user",
            message=str(exc),
        )
        _clear_state_cookie(response)
        return response
    except (LookupError, ValueError) as exc:
        conn.rollback()
        response = _error_response(
            status_code=status.HTTP_409_CONFLICT,
            code="sso_identity_conflict",
            message=str(exc),
        )
        _clear_state_cookie(response)
        return response
    except GraphAPIError as exc:
        conn.rollback()
        response = _error_response(exc.status_code, exc.code, exc.message, exc.details)
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

    settings = get_settings()
    response = RedirectResponse(url=settings.frontend_url, status_code=status.HTTP_302_FOUND)
    _set_auth_cookies(response, auth_tokens)
    response.set_cookie(
        key=SESSION_TOKEN_COOKIE_NAME,
        value=token_payload["access_token"],
        **build_auth_cookie_settings(max_age=settings.session_ttl),
    )
    _clear_state_cookie(response)
    return response


@router.get("/graph/me", response_model=None)
def graph_me(
    request: Request,
    _: Annotated[dict[str, Any], Depends(get_current_user)],
):
    try:
        return fetch_graph_me(_require_graph_access_token(request))
    except GraphAPIError as exc:
        return _error_response(exc.status_code, exc.code, exc.message, exc.details)


@router.get("/graph/groups", response_model=None)
def graph_groups(
    request: Request,
    _: Annotated[dict[str, Any], Depends(get_current_user)],
):
    try:
        return fetch_graph_groups(_require_graph_access_token(request))
    except GraphAPIError as exc:
        return _error_response(exc.status_code, exc.code, exc.message, exc.details)


@router.get("/graph/manager", response_model=None)
def graph_manager(
    request: Request,
    _: Annotated[dict[str, Any], Depends(get_current_user)],
):
    try:
        return fetch_graph_manager(_require_graph_access_token(request))
    except GraphAPIError as exc:
        return _error_response(exc.status_code, exc.code, exc.message, exc.details)


def _provision_first_time_user(
    conn: PGConnection,
    *,
    tenant_id: str,
    azure_tenant_id: str,
    microsoft_object_id: str,
    claims: dict[str, Any],
    graph_profile: dict[str, Any],
    graph_manager: dict[str, Any],
    graph_groups: dict[str, Any],
) -> dict[str, Any]:
    """Create the app user and Graph enrichment rows required on first login."""
    manager_graph_object_id = _resolve_manager_subject_identifier(graph_manager)
    manager_user_id = None
    if manager_graph_object_id:
        manager_user = fetch_user_by_microsoft_object_id(
            conn,
            tenant_id=tenant_id,
            microsoft_object_id=manager_graph_object_id,
        )
        if manager_user is not None:
            manager_user_id = str(manager_user["user_id"])

    email = _resolve_email(claims, graph_profile)
    user_principal_name = _resolve_user_principal_name(claims, graph_profile)
    display_name = _resolve_display_name(claims, graph_profile)
    full_name = _resolve_full_name(display_name=display_name, email=email)

    user = create_app_user_from_graph(
        conn,
        tenant_id=tenant_id,
        microsoft_object_id=microsoft_object_id,
        email=email,
        full_name=full_name,
        user_principal_name=user_principal_name,
        display_name=display_name,
        mobile_phone=_resolve_optional_graph_text(graph_profile, "mobilePhone"),
        office_location=_resolve_optional_graph_text(graph_profile, "officeLocation"),
        job_title=_resolve_optional_graph_text(graph_profile, "jobTitle"),
        department=_resolve_optional_graph_text(graph_profile, "department"),
        company_name=_resolve_optional_graph_text(graph_profile, "companyName"),
        employee_id=_resolve_optional_graph_text(graph_profile, "employeeId"),
        manager_user_id=manager_user_id,
    )
    user_id = str(user["user_id"])
    create_auth_identity_for_user(
        conn,
        tenant_id=tenant_id,
        user_id=user_id,
        provider=MICROSOFT_PROVIDER,
        provider_tenant_id=azure_tenant_id,
        provider_user_id=microsoft_object_id,
        email=email,
        raw_profile=graph_profile,
    )
    upsert_user_graph_profile(
        conn,
        tenant_id=tenant_id,
        user_id=user_id,
        graph_profile=graph_profile,
        manager_graph_object_id=manager_graph_object_id,
    )
    sync_graph_groups_for_user(
        conn,
        tenant_id=tenant_id,
        user_id=user_id,
        graph_groups=graph_groups,
    )
    resolved = fetch_user_by_id(conn, tenant_id=tenant_id, user_id=user_id)
    if resolved is None:
        raise LookupError("Created SSO user could not be reloaded.")
    return resolved


def _fetch_graph_payload(
    fetcher: Callable[[str], dict[str, Any]],
    access_token: str,
    *,
    required: bool,
) -> dict[str, Any]:
    try:
        return fetcher(access_token)
    except GraphAPIError as exc:
        if not required and exc.status_code == status.HTTP_404_NOT_FOUND:
            return {}
        raise


def _resolve_claim_object_id(claims: dict[str, Any]) -> str:
    for candidate in (claims.get("oid"), claims.get("sub")):
        normalized = str(candidate or "").strip()
        if normalized:
            return normalized
    return ""


def _resolve_graph_object_id(graph_profile: dict[str, Any]) -> str:
    graph_object_id = str(graph_profile.get("id") or "").strip()
    if not graph_object_id:
        raise ValueError("Microsoft Graph /me did not include id.")
    if len(graph_object_id) > 150:
        raise ValueError("Microsoft Graph /me id exceeds app_users.microsoft_object_id length.")
    return graph_object_id


def _resolve_email(claims: dict[str, Any], graph_profile: dict[str, Any]) -> str:
    for candidate in (
        graph_profile.get("mail"),
        graph_profile.get("userPrincipalName"),
        claims.get("preferred_username"),
        claims.get("email"),
    ):
        normalized = str(candidate or "").strip().lower()
        if normalized:
            if len(normalized) > 200:
                raise ValueError("Resolved email exceeds app_users.email length.")
            return normalized
    raise ValueError("Microsoft identity did not include mail or userPrincipalName.")


def _resolve_user_principal_name(claims: dict[str, Any], graph_profile: dict[str, Any]) -> str | None:
    for candidate in (graph_profile.get("userPrincipalName"), claims.get("preferred_username")):
        normalized = str(candidate or "").strip()
        if normalized:
            if len(normalized) > 200:
                raise ValueError("userPrincipalName exceeds schema length.")
            return normalized
    return None


def _resolve_display_name(claims: dict[str, Any], graph_profile: dict[str, Any]) -> str | None:
    for candidate in (
        graph_profile.get("displayName"),
        claims.get("name"),
    ):
        normalized = str(candidate or "").strip()
        if normalized:
            if len(normalized) > 200:
                raise ValueError("displayName exceeds schema length.")
            return normalized
    return None


def _resolve_full_name(*, display_name: str | None, email: str) -> str:
    full_name = str(display_name or email).strip()
    if not full_name:
        raise ValueError("full_name could not be resolved from Microsoft Graph.")
    if len(full_name) > 200:
        raise ValueError("Resolved full_name exceeds app_users.full_name length.")
    return full_name


def _resolve_optional_graph_text(graph_profile: dict[str, Any], key: str) -> str | None:
    normalized = str(graph_profile.get(key) or "").strip()
    return normalized or None


def _resolve_manager_subject_identifier(graph_manager: dict[str, Any]) -> str | None:
    manager_id = str(graph_manager.get("id") or "").strip()
    if manager_id and len(manager_id) > 150:
        raise ValueError("Manager Graph id exceeds schema length.")
    return manager_id or None


def _require_graph_access_token(request: Request) -> str:
    access_token = str(request.cookies.get(SESSION_TOKEN_COOKIE_NAME) or "").strip()
    if not access_token:
        raise GraphAPIError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="missing_graph_session",
            message="Microsoft Graph access token is missing from the current session.",
        )
    return access_token


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


def _clear_state_cookie(response: Response) -> None:
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
    content: dict[str, Any] = {
        "error": {
            "code": code,
            "message": message,
        }
    }
    if details:
        content["error"]["details"] = details
    return JSONResponse(status_code=status_code, content=content)
