from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
import uuid

import psycopg2
from fastapi import HTTPException, status
from psycopg2 import errorcodes
from psycopg2.extensions import TRANSACTION_STATUS_IDLE
from psycopg2.extensions import connection as PGConnection

from backend.core.security import (
    TokenError,
    build_jwt_payload,
    create_refresh_token,
    hash_password,
    hash_token,
    sign_jwt,
    verify_password,
)
from backend.repositories.token_repository import (
    fetch_refresh_token_by_hash,
    revoke_refresh_token,
    revoke_refresh_token_family,
    store_refresh_token,
)
from backend.repositories.user_repository import create_user, fetch_user_by_email, fetch_user_by_id
from backend.schemas.auth import LoginRequest, MessageResponse, SignupRequest, UserResponse


@dataclass(frozen=True)
class AuthTokens:
    access_token: str
    refresh_token: str


def _rollback_if_needed(conn: PGConnection) -> None:
    if conn.closed:
        return
    if conn.get_transaction_status() != TRANSACTION_STATUS_IDLE:
        conn.rollback()


def _build_access_token_for_user(user: dict[str, Any]) -> str:
    extra_claims: dict[str, Any] = {}

    role = str(user.get("role") or "").strip()
    if role:
        extra_claims["role"] = role

    tenant = user.get("tenant_id", user.get("tenant"))
    if tenant is not None and str(tenant).strip():
        extra_claims["tenant"] = str(tenant).strip()

    payload = build_jwt_payload(
        user,
        extra_claims=extra_claims or None,
    )
    return sign_jwt(payload)


def _persist_auth_tokens(
    conn: PGConnection,
    *,
    user: dict[str, Any],
    rotate_from_token_id: str | None = None,
) -> AuthTokens:
    refresh_data = create_refresh_token()
    access_token = _build_access_token_for_user(user)

    store_refresh_token(
        conn,
        token_id=refresh_data["id"],
        user_id=str(user["user_id"]),
        token_hash=refresh_data["token_hash"],
        expires_at=refresh_data["expires_at"],
    )

    if rotate_from_token_id is not None:
        revoked = revoke_refresh_token(
            conn,
            token_id=rotate_from_token_id,
            replaced_by_token_id=refresh_data["id"],
        )
        if not revoked:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "code": "refresh_token_rotation_failed",
                    "message": "Refresh token could not be rotated because it is no longer active.",
                },
            )

    return AuthTokens(
        access_token=access_token,
        refresh_token=refresh_data["token"],
    )


def signup_user(conn: PGConnection, payload: SignupRequest) -> UserResponse:
    normalized_email = payload.email.strip().lower()
    try:
        existing_user = fetch_user_by_email(conn, normalized_email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )

        created_user = create_user(
            conn,
            user_id=str(uuid.uuid4()),
            name=payload.name.strip(),
            email=normalized_email,
            password_hash=hash_password(payload.password),
            location=payload.location.strip(),
            project=int(payload.project),
            role=payload.role.strip(),
        )
        conn.commit()
    except HTTPException:
        _rollback_if_needed(conn)
        raise
    except psycopg2.Error as exc:
        _rollback_if_needed(conn)
        if exc.pgcode == errorcodes.UNIQUE_VIOLATION:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user",
        ) from exc

    return UserResponse(**created_user)


def login_user(conn: PGConnection, payload: LoginRequest) -> AuthTokens:
    normalized_email = payload.email.strip().lower()
    try:
        user = fetch_user_by_email(conn, normalized_email)
    except psycopg2.Error as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "login_failed",
                "message": "Failed to process login.",
            },
        ) from exc

    if user is None or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "invalid_credentials",
                "message": "Invalid email or password.",
            },
        )

    try:
        auth_tokens = issue_tokens_for_user(conn, user, commit=False)
        conn.commit()
        return auth_tokens
    except HTTPException:
        _rollback_if_needed(conn)
        raise
    except psycopg2.Error as exc:
        _rollback_if_needed(conn)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "token_issue_failed",
                "message": "Failed to issue authentication tokens.",
            },
        ) from exc


def issue_tokens_for_user(
    conn: PGConnection,
    user: dict[str, Any],
    *,
    commit: bool = True,
) -> AuthTokens:
    try:
        auth_tokens = _persist_auth_tokens(conn, user=user)
        if commit:
            conn.commit()
        return auth_tokens
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
    commit: bool = True,
) -> AuthTokens:
    try:
        token_hash = hash_token(refresh_token)
    except TokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "missing_refresh_token",
                "message": str(exc),
            },
        ) from exc

    try:
        token_record = fetch_refresh_token_by_hash(conn, token_hash)
        if token_record is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "code": "invalid_refresh_token",
                    "message": "Refresh token is invalid.",
                },
            )

        if token_record["revoked"]:
            if token_record.get("replaced_by_token_id"):
                revoke_refresh_token_family(conn, token_id=str(token_record["id"]))
                if commit:
                    conn.commit()
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={
                        "code": "refresh_token_reuse_detected",
                        "message": "Refresh token replay detected. The token family has been revoked.",
                    },
                )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "code": "revoked_refresh_token",
                    "message": "Refresh token has already been revoked.",
                },
            )

        expires_at = token_record["expires_at"]
        if expires_at is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "code": "expired_refresh_token",
                    "message": "Refresh token has expired.",
                },
            )
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at <= datetime.now(timezone.utc):
            revoke_refresh_token(conn, token_id=str(token_record["id"]))
            if commit:
                conn.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "code": "expired_refresh_token",
                    "message": "Refresh token has expired.",
                },
            )

        user = fetch_user_by_id(conn, str(token_record["user_id"]))
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "code": "user_not_found",
                    "message": "User not found for refresh token.",
                },
            )

        auth_tokens = _persist_auth_tokens(
            conn,
            user=user,
            rotate_from_token_id=str(token_record["id"]),
        )
        if commit:
            conn.commit()
        return auth_tokens
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


def logout_user(
    conn: PGConnection,
    *,
    refresh_token: str | None,
) -> MessageResponse:
    if not refresh_token:
        return MessageResponse(message="Logged out successfully")

    try:
        token_hash = hash_token(refresh_token)
    except TokenError:
        return MessageResponse(message="Logged out successfully")

    try:
        token_record = fetch_refresh_token_by_hash(conn, token_hash)
        if token_record is not None and not token_record["revoked"]:
            revoke_refresh_token(conn, token_id=str(token_record["id"]))
        conn.commit()
    except psycopg2.Error as exc:
        _rollback_if_needed(conn)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "logout_failed",
                "message": "Failed to logout.",
            },
        ) from exc

    return MessageResponse(message="Logged out successfully")
