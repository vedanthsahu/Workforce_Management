import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import pyotp
from fastapi import HTTPException, status
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from core.config import get_settings
from core.security import (
    build_session_payload,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from models.tables import AuthSession, LoginEvent, UserAccount, UserIdentity

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── Password utilities ────────────────────────

def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ── TOTP utilities ────────────────────────────

def generate_totp_secret() -> str:
    return pyotp.random_base32()


def get_totp_uri(secret: str, email: str, issuer: str = "SeatBooking") -> str:
    """Returns otpauth:// URI — used to generate QR code."""
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=email, issuer_name=issuer)


def verify_totp_code(secret: str, code: str) -> bool:
    """Validates a 6-digit TOTP code with ±1 window (30-sec tolerance)."""
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=1)


# ── User management ───────────────────────────

def get_user_by_email(email: str, tenant_id: str, db: Session) -> UserAccount | None:
    return db.query(UserAccount).filter_by(email=email, tenant_id=tenant_id).first()


def create_password_user(
    email: str,
    password: str,
    tenant_id: str,
    display_name: str | None,
    db: Session,
) -> UserAccount:
    existing = get_user_by_email(email, tenant_id, db)
    if existing:
        raise HTTPException(status_code=409, detail="User already exists for this tenant")

    user = UserAccount(
        tenant_id=tenant_id,
        email=email,
        display_name=display_name or email.split("@")[0],
        role="employee",
        auth_type="password",
        pwd_hash=hash_password(password),
        totp_secret=generate_totp_secret(),
        totp_verified=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def upsert_sso_user(
    email: str,
    tenant_id: str,
    idp_id: str,
    external_id: str,
    display_name: str | None,
    db: Session,
) -> UserAccount:
    """
    Find-or-create a user after successful SSO.
    Binds UserIdentity (external_id → platform user).
    """
    # Check if we already have this identity
    identity = (
        db.query(UserIdentity)
        .filter_by(idp_id=idp_id, external_id=external_id)
        .first()
    )
    if identity:
        user = db.query(UserAccount).filter_by(user_id=identity.user_id).first()
        user.last_login = datetime.now(timezone.utc)
        db.commit()
        return user

    # No identity yet — find or create user account
    user = get_user_by_email(email, tenant_id, db)
    if not user:
        user = UserAccount(
            tenant_id=tenant_id,
            email=email,
            display_name=display_name or email.split("@")[0],
            role="employee",
            auth_type="sso",
        )
        db.add(user)
        db.flush()

    # Bind identity
    new_identity = UserIdentity(
        user_id=user.user_id,
        idp_id=idp_id,
        external_id=external_id,
    )
    db.add(new_identity)
    user.last_login = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)
    return user


# ── Session management ────────────────────────

def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def issue_tokens(user: UserAccount, db: Session) -> dict:
    """Issue access + refresh tokens and persist session to DB."""
    payload = build_session_payload(
        user_id=user.user_id,
        email=user.email,
        tenant_id=user.tenant_id,
        role=user.role,
        auth_type=user.auth_type,
    )
    access_token = create_access_token(payload)
    refresh_token = create_refresh_token(payload)

    session = AuthSession(
        user_id=user.user_id,
        tenant_id=user.tenant_id,
        refresh_token_hash=_hash_token(refresh_token),
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(session)
    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


def rotate_refresh_token(refresh_token: str, db: Session) -> dict:
    """Validate refresh token, revoke old session, issue new tokens."""
    try:
        payload = decode_token(refresh_token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Not a refresh token")

    token_hash = _hash_token(refresh_token)
    session = db.query(AuthSession).filter_by(refresh_token_hash=token_hash, is_revoked=False).first()
    if not session:
        raise HTTPException(status_code=401, detail="Session not found or already revoked")

    if session.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Refresh token expired — please log in again")

    # Revoke old session
    session.is_revoked = True
    db.commit()

    user = db.query(UserAccount).filter_by(user_id=session.user_id).first()
    return issue_tokens(user, db)


def revoke_session(refresh_token: str, db: Session):
    token_hash = _hash_token(refresh_token)
    session = db.query(AuthSession).filter_by(refresh_token_hash=token_hash).first()
    if session:
        session.is_revoked = True
        db.commit()


# ── Audit ─────────────────────────────────────

def log_login_event(
    db: Session,
    tenant_id: str,
    email: str,
    auth_type: str,
    success: bool,
    user_id: str | None = None,
    failure_reason: str | None = None,
    ip_address: str | None = None,
):
    event = LoginEvent(
        tenant_id=tenant_id,
        user_id=user_id,
        email=email,
        auth_type=auth_type,
        success=success,
        failure_reason=failure_reason,
        ip_address=ip_address,
    )
    db.add(event)
    db.commit()
