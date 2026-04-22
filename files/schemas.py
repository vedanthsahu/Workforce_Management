from pydantic import BaseModel, EmailStr
from typing import Optional
from enum import Enum


class AuthTypeEnum(str, Enum):
    sso = "sso"
    password = "password"


# ── Tenant discovery ──────────────────────────

class TenantDiscoverRequest(BaseModel):
    email: EmailStr


class TenantDiscoverResponse(BaseModel):
    tenant_id: str
    tenant_name: str
    domain: str
    sso_enabled: bool
    idp_type: Optional[str]           # "oidc" | "saml" | None
    password_auth_allowed: bool


# ── SSO ───────────────────────────────────────

class SSOInitiateRequest(BaseModel):
    email: EmailStr


class SSOInitiateResponse(BaseModel):
    redirect_url: str
    idp_type: str


# ── Password + TOTP auth ──────────────────────

class PasswordLoginRequest(BaseModel):
    email: EmailStr
    password: str


class TOTPVerifyRequest(BaseModel):
    email: EmailStr
    tenant_id: str
    totp_code: str


class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str
    display_name: Optional[str] = None


class TOTPSetupResponse(BaseModel):
    totp_secret: str
    qr_code_uri: str       # otpauth:// URI for QR generation
    message: str


# ── Session tokens ────────────────────────────

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int         # seconds


class RefreshRequest(BaseModel):
    refresh_token: str


# ── Current user ──────────────────────────────

class CurrentUserResponse(BaseModel):
    user_id: str
    email: str
    tenant_id: str
    role: str
    auth_type: str


# ── Generic ───────────────────────────────────

class MessageResponse(BaseModel):
    message: str
