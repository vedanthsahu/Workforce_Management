from typing import Annotated, Any

import psycopg2
import requests
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from psycopg2.extensions import connection as PGConnection

from backend.core.config import get_settings
from backend.core.sso import (
    _build_auth_url,
    _create_session,
    _verify_id_token,
    clear_session,
    consume_login_state,
    get_active_session,
    get_cookie_settings,
    get_redirect_uri,
    get_token_url,
)
from backend.db.connection import get_db
from backend.repositories.user_repository import upsert_user_from_sso

router = APIRouter()


@router.get("/login-page", response_class=HTMLResponse)
def auth_login_page() -> HTMLResponse:
    # SSO: browser helper page that immediately redirects to Microsoft login.
    auth_url, _ = _build_auth_url()
    return HTMLResponse(
        content=(
            "<!DOCTYPE html>"
            "<html><head><title>Redirecting...</title></head>"
            "<body>"
            "<p>Redirecting to Microsoft login...</p>"
            f'<p>If you are not redirected, <a href="{auth_url}">click here</a>.</p>'
            f'<script>window.location.href = "{auth_url}";</script>'
            "</body></html>"
        )
    )


@router.get("/callback")
def auth_callback(
    conn: Annotated[PGConnection, Depends(get_db)],
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
) -> RedirectResponse:
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Microsoft auth error: {error} - {error_description or 'unknown'}",
        )
    if not code or not state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing code or state in callback",
        )

    # SSO: CSRF protection via one-time state token.
    consume_login_state(state)

    settings = get_settings()
    try:
        token_response = requests.post(
            get_token_url(),
            data={
                "client_id": settings.azure_client_id,
                "client_secret": settings.azure_client_secret,
                "code": code,
                "redirect_uri": get_redirect_uri(),
                "grant_type": "authorization_code",
            },
            timeout=10,
        )
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to exchange auth code with Microsoft",
        ) from exc

    if token_response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Microsoft token exchange failed",
        )

    token_payload: dict[str, Any] = token_response.json()
    id_token = token_payload.get("id_token")
    if not id_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Microsoft response did not include id_token",
        )

    # SSO: verify JWT signature/audience/issuer and map claims.
    claims = _verify_id_token(str(id_token))
    azure_oid = str(claims.get("oid") or "").strip()
    claim_email = claims.get("preferred_username") or claims.get("email")
    email = str(claim_email or "").strip().lower()
    raw_display_name = claims.get("name")
    display_name = str(raw_display_name).strip() if raw_display_name else None

    if not azure_oid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token missing required oid claim",
        )
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token missing email/preferred_username claim",
        )

    try:
        # SSO: upsert user profile via raw SQL.
        user = upsert_user_from_sso(
            conn,
            azure_oid=azure_oid,
            email=email,
            display_name=display_name,
        )
        conn.commit()
    except psycopg2.Error as exc:
        conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create or update SSO user",
        ) from exc

    session_token = _create_session(
        user_id=str(user["user_id"]),
        email=str(user["email"]),
    )
    response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    response.set_cookie(
        key="session_token",
        value=session_token,
        **get_cookie_settings(),
    )
    return response


@router.get("/session-check")
def auth_session_check(request: Request) -> dict[str, Any]:
    # SSO: non-throwing session probe for frontend polling.
    session_token = request.cookies.get("session_token")
    session = get_active_session(session_token)
    if session is None:
        return {"authenticated": False}
    return {
        "authenticated": True,
        "email": session["email"],
        "user_id": session["user_id"],
    }


@router.get("/logout")
def auth_logout(request: Request) -> RedirectResponse:
    # SSO: clear local in-memory session and cookie.
    session_token = request.cookies.get("session_token")
    clear_session(session_token)
    response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    response.delete_cookie("session_token", path="/")
    return response
