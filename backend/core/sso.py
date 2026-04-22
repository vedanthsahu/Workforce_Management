from datetime import datetime, timezone
from typing import Annotated, Any
import secrets
import time
from urllib.parse import urlencode, urlparse

import psycopg2
import requests
from fastapi import Depends, HTTPException, Request, status
from jose import ExpiredSignatureError, JWTError, jwt
from psycopg2.extensions import connection as PGConnection

from backend.core.config import get_settings
from backend.db.connection import get_db
from backend.repositories.user_repository import fetch_user_by_id

# SSO: in-memory TTLs for CSRF states and authenticated sessions.
STATE_TTL_SECONDS = 600
SESSION_TTL_SECONDS = 3600

# SSO: in-memory stores (single-process only).
login_states: dict[str, float] = {}
sessions: dict[str, dict[str, Any]] = {}


def _authorize_url() -> str:
    settings = get_settings()
    return (
        f"https://login.microsoftonline.com/"
        f"{settings.azure_tenant_id}/oauth2/v2.0/authorize"
    )


def get_token_url() -> str:
    settings = get_settings()
    return f"https://login.microsoftonline.com/{settings.azure_tenant_id}/oauth2/v2.0/token"


def _jwks_url() -> str:
    settings = get_settings()
    return f"https://login.microsoftonline.com/{settings.azure_tenant_id}/discovery/v2.0/keys"


def get_redirect_uri() -> str:
    settings = get_settings()
    base = settings.public_base_url.rstrip("/")
    return f"{base}/auth/callback"


def _is_localhost_base_url(public_base_url: str) -> bool:
    hostname = urlparse(public_base_url).hostname
    return hostname in {"localhost", "127.0.0.1"}


def get_cookie_settings() -> dict[str, Any]:
    settings = get_settings()
    # SSO: secure cookie follows URL scheme; localhost uses lax for dev.
    secure = urlparse(settings.public_base_url).scheme == "https"
    is_localhost = _is_localhost_base_url(settings.public_base_url)
    same_site = "lax" if is_localhost else ("none" if secure else "lax")
    return {
        "httponly": True,
        "secure": secure,
        "samesite": same_site,
        "max_age": SESSION_TTL_SECONDS,
        "path": "/",
    }


def _purge_expired_states() -> None:
    # SSO: remove stale CSRF states before creating/consuming new states.
    now = time.time()
    expired = [state for state, created_at in login_states.items() if now - created_at > STATE_TTL_SECONDS]
    for state in expired:
        login_states.pop(state, None)


def _purge_expired_sessions() -> None:
    # SSO: remove stale in-memory sessions.
    now = time.time()
    expired = [token for token, session in sessions.items() if now - session["created_at"] > SESSION_TTL_SECONDS]
    for token in expired:
        sessions.pop(token, None)


def _build_auth_url() -> tuple[str, str]:
    # SSO: create one-time CSRF state and authorization URL.
    settings = get_settings()
    _purge_expired_states()
    state = secrets.token_urlsafe(24)
    login_states[state] = time.time()

    params = urlencode(
        {
            "client_id": settings.azure_client_id,
            "response_type": "code",
            "redirect_uri": get_redirect_uri(),
            "scope": "openid profile email",
            "state": state,
            "prompt": "select_account",
        }
    )
    return f"{_authorize_url()}?{params}", state


def consume_login_state(state: str) -> None:
    _purge_expired_states()
    created_at = login_states.pop(state, None)
    if created_at is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired login state",
        )
    if time.time() - created_at > STATE_TTL_SECONDS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Login state has expired",
        )


def _verify_id_token(id_token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        jwks_response = requests.get(_jwks_url(), timeout=10)
        jwks_response.raise_for_status()
        jwks = jwks_response.json()
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch Microsoft JWKS",
        ) from exc

    try:
        claims = jwt.decode(
            id_token,
            jwks,
            algorithms=["RS256"],
            audience=settings.azure_client_id,
            options={"verify_iss": False},
        )
    except ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Microsoft id_token has expired",
        ) from exc
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Microsoft id_token",
        ) from exc

    # SSO: issuer must match the configured tenant.
    issuer = str(claims.get("iss") or "")
    expected_issuer_prefix = f"https://login.microsoftonline.com/{settings.azure_tenant_id}"
    if not issuer.startswith(expected_issuer_prefix):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Microsoft token issuer",
        )
    return claims


def _create_session(*, user_id: str, email: str) -> str:
    # SSO: issue in-memory session token.
    _purge_expired_sessions()
    session_token = secrets.token_urlsafe(32)
    sessions[session_token] = {
        "user_id": user_id,
        "email": email,
        "created_at": time.time(),
    }
    return session_token


def get_active_session(session_token: str | None) -> dict[str, Any] | None:
    _purge_expired_sessions()
    if not session_token:
        return None
    session = sessions.get(session_token)
    if session is None:
        return None
    if time.time() - session["created_at"] > SESSION_TTL_SECONDS:
        sessions.pop(session_token, None)
        return None
    return session


def clear_session(session_token: str | None) -> None:
    if session_token:
        sessions.pop(session_token, None)


def get_current_sso_user(
    request: Request,
    conn: Annotated[PGConnection, Depends(get_db)],
) -> dict[str, Any]:
    # SSO: cookie-based authenticated user loader.
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing session cookie",
        )

    session = get_active_session(session_token)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or not found",
        )

    try:
        user = fetch_user_by_id(conn, str(session["user_id"]))
    except psycopg2.Error as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch authenticated SSO user",
        ) from exc

    if user is None:
        clear_session(session_token)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user not found",
        )

    return user


def current_utc_timestamp() -> datetime:
    return datetime.now(timezone.utc)
