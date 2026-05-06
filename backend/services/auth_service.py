"""Authentication service orchestration for SSO-backed sessions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import psycopg2
from fastapi import HTTPException, status
from psycopg2.extensions import TRANSACTION_STATUS_IDLE
from psycopg2.extensions import connection as PGConnection

from backend.core.security import (
    TokenError,
    build_jwt_payload,
    create_scoped_refresh_token,
    hash_token,
    parse_refresh_token,
    sign_jwt,
)
from backend.repositories.token_repository import (
    create_user_session,
    fetch_session_by_refresh_token,
    record_auth_event,
    revoke_user_session,
    rotate_refresh_token,
)
from backend.repositories.user_repository import fetch_user_by_id


@dataclass(frozen=True)
class AuthTokens:
    """Access and refresh tokens issued together for one authenticated session."""

    access_token: str
    refresh_token: str


def _rollback_if_needed(conn: PGConnection) -> None:
    if conn.closed:
        return
    if conn.get_transaction_status() != TRANSACTION_STATUS_IDLE:
        conn.rollback()


def _build_access_token_for_user(user: dict[str, Any], *, session_id: str) -> str:
    extra_claims: dict[str, Any] = {
        "user_id": str(user["user_id"]),
        "tenant_id": str(user["tenant_id"]),
        "session_id": session_id,
    }

    role = str(user.get("role") or "").strip()
    if role:
        extra_claims["role"] = role

    payload = build_jwt_payload(user, extra_claims=extra_claims)
    return sign_jwt(payload)


def issue_tokens_for_user(
    conn: PGConnection,
    user: dict[str, Any],
    *,
    user_agent: str | None = None,
    ip_address: str | None = None,
    commit: bool = True,
) -> AuthTokens:
    """Create one DB-backed session and issue the corresponding token pair."""
    session_id = str(uuid4())
    refresh_data = create_scoped_refresh_token(
        tenant_id=str(user["tenant_id"]),
        user_id=str(user["user_id"]),
        session_id=session_id,
    )

    try:
        create_user_session(
            conn,
            session_id=session_id,
            tenant_id=str(user["tenant_id"]),
            user_id=str(user["user_id"]),
            refresh_token_hash=refresh_data["token_hash"],
            user_agent=user_agent,
            ip_address=ip_address,
            expires_at=refresh_data["expires_at"],
        )
        record_auth_event(
            conn,
            tenant_id=str(user["tenant_id"]),
            user_id=str(user["user_id"]),
            session_id=session_id,
            event_type="LOGIN",
        )
        access_token = _build_access_token_for_user(user, session_id=session_id)
        if commit:
            conn.commit()
        return AuthTokens(
            access_token=access_token,
            refresh_token=refresh_data["token"],
        )
    except HTTPException:
        if commit:
            _rollback_if_needed(conn)
        raise
    except psycopg2.Error as exc:
        if commit:
            _rollback_if_needed(conn)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "token_issue_failed",
                "message": "Failed to issue authentication tokens.",
            },
        ) from exc


def refresh_auth_tokens(
    conn: PGConnection,
    refresh_token: str,
    *,
    user_agent: str | None = None,
    ip_address: str | None = None,
    commit: bool = True,
) -> AuthTokens:
    """Rotate the refresh token for one existing user_session row."""
    try:
        refresh_scope = parse_refresh_token(refresh_token)
        token_hash = hash_token(refresh_token)
    except TokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "invalid_refresh_token",
                "message": str(exc),
            },
        ) from exc

    try:
        session = fetch_session_by_refresh_token(
            conn,
            tenant_id=refresh_scope["tenant_id"],
            user_id=refresh_scope["user_id"],
            session_id=refresh_scope["session_id"],
            refresh_token_hash=token_hash,
        )
        if session is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "code": "invalid_refresh_token",
                    "message": "Refresh token is invalid.",
                },
            )

        if session["is_revoked"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "code": "revoked_refresh_token",
                    "message": "Refresh token has already been revoked.",
                },
            )

        expires_at = session["expires_at"]
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at <= datetime.now(timezone.utc):
            revoke_user_session(
                conn,
                tenant_id=refresh_scope["tenant_id"],
                user_id=refresh_scope["user_id"],
                session_id=refresh_scope["session_id"],
                refresh_token_hash=token_hash,
            )
            if commit:
                conn.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "code": "expired_refresh_token",
                    "message": "Refresh token has expired.",
                },
            )

        user = fetch_user_by_id(
            conn,
            tenant_id=refresh_scope["tenant_id"],
            user_id=refresh_scope["user_id"],
        )
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "code": "user_not_found",
                    "message": "User not found for refresh token.",
                },
            )

        rotated_refresh = create_scoped_refresh_token(
            tenant_id=refresh_scope["tenant_id"],
            user_id=refresh_scope["user_id"],
            session_id=refresh_scope["session_id"],
        )
        rotated_session = rotate_refresh_token(
            conn,
            tenant_id=refresh_scope["tenant_id"],
            user_id=refresh_scope["user_id"],
            session_id=refresh_scope["session_id"],
            current_refresh_token_hash=token_hash,
            new_refresh_token_hash=rotated_refresh["token_hash"],
            user_agent=user_agent,
            ip_address=ip_address,
            expires_at=rotated_refresh["expires_at"],
        )
        if rotated_session is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "code": "refresh_token_rotation_failed",
                    "message": "Refresh token could not be rotated because the session is no longer active.",
                },
            )

        record_auth_event(
            conn,
            tenant_id=refresh_scope["tenant_id"],
            user_id=refresh_scope["user_id"],
            session_id=refresh_scope["session_id"],
            event_type="REFRESH",
        )
        access_token = _build_access_token_for_user(
            user,
            session_id=refresh_scope["session_id"],
        )
        if commit:
            conn.commit()
        return AuthTokens(
            access_token=access_token,
            refresh_token=rotated_refresh["token"],
        )
    except HTTPException:
        if commit:
            _rollback_if_needed(conn)
        raise
    except psycopg2.Error as exc:
        if commit:
            _rollback_if_needed(conn)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "refresh_failed",
                "message": "Failed to refresh authentication tokens.",
            },
        ) from exc
