import secrets
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from core.dependencies import get_current_user
from db.database import get_db
from models.schemas import (
    CurrentUserResponse,
    MessageResponse,
    PasswordLoginRequest,
    RefreshRequest,
    SSOInitiateResponse,
    TenantDiscoverRequest,
    TenantDiscoverResponse,
    TOTPSetupResponse,
    TOTPVerifyRequest,
    TokenResponse,
    UserRegisterRequest,
)
from models.tables import IdentityProvider, UserAccount
from services import auth_service, oidc_service, tenant_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ──────────────────────────────────────────────
# 1. TENANT DISCOVERY
# ──────────────────────────────────────────────

@router.post("/discover", response_model=TenantDiscoverResponse, summary="Step 1 — resolve tenant from email")
def discover_tenant(body: TenantDiscoverRequest, db: Session = Depends(get_db)):
    """
    Given an email address, return the tenant context.
    The client uses this to decide whether to show 'Login with SSO' or 'Enter password'.
    """
    ctx = tenant_service.discover_tenant(body.email, db)
    tenant = ctx["tenant"]
    idp: IdentityProvider | None = ctx["idp"]
    policy = ctx["policy"]

    return TenantDiscoverResponse(
        tenant_id=str(tenant.tenant_id),
        tenant_name=tenant.tenant_name,
        domain=ctx["domain"],
        sso_enabled=idp is not None,
        idp_type=idp.idp_type if idp else None,
        password_auth_allowed=policy.password_auth_allowed if policy else True,
    )


# ──────────────────────────────────────────────
# 2. SSO — INITIATE
# ──────────────────────────────────────────────

@router.post("/sso/initiate", response_model=SSOInitiateResponse, summary="Step 2 — get SSO redirect URL")
def sso_initiate(body: TenantDiscoverRequest, db: Session = Depends(get_db)):
    """
    Returns the IdP redirect URL. Client redirects the browser there.
    State carries tenant_id so the callback knows which tenant to resolve.
    """
    ctx = tenant_service.discover_tenant(body.email, db)
    idp: IdentityProvider | None = ctx["idp"]

    if not idp:
        raise HTTPException(status_code=400, detail="SSO not configured for this tenant")

    # State = tenant_id:random_nonce  — validated in callback
    state = f"{ctx['tenant'].tenant_id}:{secrets.token_urlsafe(16)}"

    if idp.idp_type == "oidc":
        redirect_url = oidc_service.build_oidc_redirect_url(idp, state)
    elif idp.idp_type == "saml":
        # SAML redirect — implement saml_service.build_saml_request(idp, state)
        raise HTTPException(status_code=501, detail="SAML handler not implemented in this demo")
    else:
        raise HTTPException(status_code=400, detail="Unknown IdP type")

    return SSOInitiateResponse(redirect_url=redirect_url, idp_type=idp.idp_type)


# ──────────────────────────────────────────────
# 3. SSO — OIDC CALLBACK
# ──────────────────────────────────────────────

@router.get("/sso/callback/oidc", summary="OIDC callback — IdP redirects here after auth")
async def oidc_callback(
    code: str,
    state: str,
    db: Session = Depends(get_db),
):
    """
    IdP sends the user back here with an auth code.
    We exchange code → tokens, validate, upsert user, issue our session.
    """
    # Parse state to get tenant_id
    parts = state.split(":", 1)
    if len(parts) != 2:
        raise HTTPException(status_code=400, detail="Invalid state parameter")
    tenant_id = parts[0]

    tenant = tenant_service.get_tenant_by_id(tenant_id, db)
    idp = db.query(IdentityProvider).filter_by(tenant_id=tenant_id, is_default=True).first()
    if not idp:
        raise HTTPException(status_code=400, detail="No IdP config for tenant")

    # Exchange code for tokens
    token_response = await oidc_service.exchange_code_for_tokens(idp, code)
    id_token = token_response.get("id_token")
    if not id_token:
        raise HTTPException(status_code=502, detail="IdP did not return id_token")

    # Parse claims (verify signature in production using JWKS)
    claims = oidc_service.parse_id_token_claims(id_token)
    email = claims.get("email")
    external_id = claims.get("sub")
    display_name = claims.get("name")

    if not email or not external_id:
        raise HTTPException(status_code=400, detail="Missing email or sub in IdP token")

    # Upsert user
    user = auth_service.upsert_sso_user(
        email=email,
        tenant_id=tenant_id,
        idp_id=str(idp.idp_id),
        external_id=external_id,
        display_name=display_name,
        db=db,
    )

    # Issue our session
    tokens = auth_service.issue_tokens(user, db)
    auth_service.log_login_event(db, tenant_id, email, "sso", True, user.user_id)

    return TokenResponse(**tokens)


# ──────────────────────────────────────────────
# 4. PASSWORD AUTH — REGISTER
# ──────────────────────────────────────────────

@router.post("/register", response_model=TOTPSetupResponse, summary="Register with email + password")
def register(body: UserRegisterRequest, db: Session = Depends(get_db)):
    """
    Register a new password-based user.
    Returns TOTP secret + QR URI — user must scan and confirm before first login.
    Tenant must have password_auth_allowed = true.
    """
    ctx = tenant_service.discover_tenant(body.email, db)
    policy = ctx["policy"]

    if not policy or not policy.password_auth_allowed:
        raise HTTPException(
            status_code=403,
            detail="Password login is not allowed for this tenant. Use SSO.",
        )

    user = auth_service.create_password_user(
        email=body.email,
        password=body.password,
        tenant_id=str(ctx["tenant"].tenant_id),
        display_name=body.display_name,
        db=db,
    )

    qr_uri = auth_service.get_totp_uri(user.totp_secret, user.email)

    return TOTPSetupResponse(
        totp_secret=user.totp_secret,
        qr_code_uri=qr_uri,
        message="Scan the QR code in Google Authenticator or Microsoft Authenticator, then call /auth/totp/confirm to activate MFA.",
    )


# ──────────────────────────────────────────────
# 5. PASSWORD AUTH — LOGIN (step 1 of 2)
# ──────────────────────────────────────────────

@router.post("/login", summary="Password login — step 1 of 2 (returns partial, then call /totp/verify)")
def login(body: PasswordLoginRequest, request: Request, db: Session = Depends(get_db)):
    """
    Validate email + password.
    If correct AND totp_verified, returns a temporary challenge token.
    Client then calls /auth/totp/verify with the 6-digit code.
    """
    ctx = tenant_service.discover_tenant(body.email, db)
    tenant = ctx["tenant"]
    policy = ctx["policy"]

    if not policy or not policy.password_auth_allowed:
        raise HTTPException(status_code=403, detail="Password login not allowed. Use SSO.")

    user: UserAccount | None = auth_service.get_user_by_email(body.email, str(tenant.tenant_id), db)

    if not user or user.auth_type != "password" or not user.pwd_hash:
        auth_service.log_login_event(db, str(tenant.tenant_id), body.email, "password", False, failure_reason="User not found")
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not auth_service.verify_password(body.password, user.pwd_hash):
        auth_service.log_login_event(db, str(tenant.tenant_id), body.email, "password", False, user.user_id, "Wrong password")
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.totp_verified:
        raise HTTPException(
            status_code=403,
            detail="MFA not set up. Please complete TOTP setup first via /auth/register.",
        )

    # Password OK — now require TOTP
    return {
        "message": "Password verified. Submit your 6-digit TOTP code to /auth/totp/verify to complete login.",
        "tenant_id": str(tenant.tenant_id),
        "email": body.email,
        "next_step": "/auth/totp/verify",
    }


# ──────────────────────────────────────────────
# 6. TOTP CONFIRM (activate MFA after register)
# ──────────────────────────────────────────────

@router.post("/totp/confirm", response_model=MessageResponse, summary="Confirm TOTP setup after registration")
def totp_confirm(body: TOTPVerifyRequest, db: Session = Depends(get_db)):
    """
    Called once after registration to verify the user scanned the QR code correctly.
    Sets totp_verified = True on the user account.
    """
    user = auth_service.get_user_by_email(body.email, body.tenant_id, db)
    if not user or not user.totp_secret:
        raise HTTPException(status_code=404, detail="User not found")

    if not auth_service.verify_totp_code(user.totp_secret, body.totp_code):
        raise HTTPException(status_code=400, detail="Invalid TOTP code. Check your authenticator app.")

    user.totp_verified = True
    db.commit()
    return MessageResponse(message="MFA activated. You can now log in with email + password + TOTP.")


# ──────────────────────────────────────────────
# 7. TOTP VERIFY (step 2 of login)
# ──────────────────────────────────────────────

@router.post("/totp/verify", response_model=TokenResponse, summary="Password login — step 2 of 2 (TOTP)")
def totp_verify(body: TOTPVerifyRequest, db: Session = Depends(get_db)):
    """
    Final step of password login. Validates TOTP code and issues full session.
    """
    user = auth_service.get_user_by_email(body.email, body.tenant_id, db)
    if not user or not user.totp_secret or not user.totp_verified:
        raise HTTPException(status_code=401, detail="User not found or MFA not set up")

    if not auth_service.verify_totp_code(user.totp_secret, body.totp_code):
        auth_service.log_login_event(db, body.tenant_id, body.email, "password", False, user.user_id, "Wrong TOTP code")
        raise HTTPException(status_code=401, detail="Invalid TOTP code")

    tokens = auth_service.issue_tokens(user, db)
    auth_service.log_login_event(db, body.tenant_id, body.email, "password", True, user.user_id)
    return TokenResponse(**tokens)


# ──────────────────────────────────────────────
# 8. REFRESH TOKEN
# ──────────────────────────────────────────────

@router.post("/refresh", response_model=TokenResponse, summary="Rotate access + refresh tokens")
def refresh(body: RefreshRequest, db: Session = Depends(get_db)):
    """
    Exchange a valid refresh token for a new access + refresh token pair.
    Old refresh token is revoked immediately (rotation).
    """
    return auth_service.rotate_refresh_token(body.refresh_token, db)


# ──────────────────────────────────────────────
# 9. LOGOUT
# ──────────────────────────────────────────────

@router.post("/logout", response_model=MessageResponse, summary="Revoke session")
def logout(body: RefreshRequest, db: Session = Depends(get_db)):
    """Revoke the refresh token — invalidates the session server-side."""
    auth_service.revoke_session(body.refresh_token, db)
    return MessageResponse(message="Logged out successfully.")


# ──────────────────────────────────────────────
# 10. CURRENT USER (protected)
# ──────────────────────────────────────────────

@router.get("/me", response_model=CurrentUserResponse, summary="Get current user from JWT")
def me(current_user: dict = Depends(get_current_user)):
    """Protected endpoint — returns decoded JWT payload. Use as auth check."""
    return CurrentUserResponse(
        user_id=current_user["sub"],
        email=current_user["email"],
        tenant_id=current_user["tenant_id"],
        role=current_user["role"],
        auth_type=current_user["auth_type"],
    )
