import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Boolean, DateTime, ForeignKey,
    Text, Enum as SAEnum, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


def utcnow():
    return datetime.now(timezone.utc)


def new_uuid():
    return str(uuid.uuid4())


# ──────────────────────────────────────────────
# COMMERCIAL
# ──────────────────────────────────────────────

class Tenant(Base):
    __tablename__ = "tenant"

    tenant_id = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    tenant_code = Column(String(64), unique=True, nullable=False)   # e.g. "test1"
    tenant_name = Column(String(255), nullable=False)
    tenant_status = Column(String(32), default="active")            # active | suspended
    created_at = Column(DateTime(timezone=True), default=utcnow)

    domains = relationship("TenantDomain", back_populates="tenant", cascade="all, delete-orphan")
    identity_providers = relationship("IdentityProvider", back_populates="tenant", cascade="all, delete-orphan")
    users = relationship("UserAccount", back_populates="tenant", cascade="all, delete-orphan")
    policy = relationship("TenantPolicy", uselist=False, back_populates="tenant", cascade="all, delete-orphan")


# ──────────────────────────────────────────────
# TENANT IDENTITY
# ──────────────────────────────────────────────

class TenantDomain(Base):
    """One or more verified login domains per tenant."""
    __tablename__ = "tenant_domain"

    id = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    tenant_id = Column(UUID(as_uuid=False), ForeignKey("tenant.tenant_id", ondelete="CASCADE"), nullable=False)
    domain_name = Column(String(255), unique=True, nullable=False)  # e.g. "test1.com"
    verified = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    tenant = relationship("Tenant", back_populates="domains")


class IdentityProvider(Base):
    """Protocol-specific SSO config per tenant. One row = one IdP."""
    __tablename__ = "identity_provider"

    idp_id = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    tenant_id = Column(UUID(as_uuid=False), ForeignKey("tenant.tenant_id", ondelete="CASCADE"), nullable=False)
    idp_type = Column(SAEnum("oidc", "saml", name="idp_type_enum"), nullable=False)
    is_default = Column(Boolean, default=True)

    # OIDC fields
    discovery_url = Column(String(512))   # /.well-known/openid-configuration
    client_id = Column(String(255))
    client_secret = Column(String(512))   # store vault ref in prod
    scopes = Column(String(255), default="openid email profile")

    # SAML fields
    metadata_url = Column(String(512))
    entity_id = Column(String(512))
    sso_url = Column(String(512))
    certificate = Column(Text)

    created_at = Column(DateTime(timezone=True), default=utcnow)
    tenant = relationship("Tenant", back_populates="identity_providers")


class TenantPolicy(Base):
    """Security policy per tenant — MFA requirements, session duration, etc."""
    __tablename__ = "tenant_policy"

    id = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    tenant_id = Column(UUID(as_uuid=False), ForeignKey("tenant.tenant_id", ondelete="CASCADE"), nullable=False, unique=True)
    mfa_required = Column(Boolean, default=True)
    password_auth_allowed = Column(Boolean, default=True)
    session_duration_minutes = Column(String(16), default="15")
    created_at = Column(DateTime(timezone=True), default=utcnow)

    tenant = relationship("Tenant", back_populates="policy")


# ──────────────────────────────────────────────
# ORGANIZATION & ACCESS
# ──────────────────────────────────────────────

class UserAccount(Base):
    """Platform-side user record. Exists independently of any IdP."""
    __tablename__ = "user_account"
    __table_args__ = (UniqueConstraint("tenant_id", "email", name="uq_tenant_email"),)

    user_id = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    tenant_id = Column(UUID(as_uuid=False), ForeignKey("tenant.tenant_id", ondelete="CASCADE"), nullable=False)
    email = Column(String(255), nullable=False)
    display_name = Column(String(255))
    role = Column(String(64), default="employee")           # employee | admin | superadmin
    auth_type = Column(SAEnum("sso", "password", name="auth_type_enum"), nullable=False)
    is_active = Column(Boolean, default=True)
    totp_secret = Column(String(64))                        # encrypted in prod — only for password users
    totp_verified = Column(Boolean, default=False)
    pwd_hash = Column(String(255))                          # bcrypt — only for password users
    last_login = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=utcnow)

    tenant = relationship("Tenant", back_populates="users")
    identities = relationship("UserIdentity", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("AuthSession", back_populates="user", cascade="all, delete-orphan")


class UserIdentity(Base):
    """Binds a platform user to their external IdP subject (sub claim)."""
    __tablename__ = "user_identity"

    id = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("user_account.user_id", ondelete="CASCADE"), nullable=False)
    idp_id = Column(UUID(as_uuid=False), ForeignKey("identity_provider.idp_id", ondelete="CASCADE"), nullable=False)
    external_id = Column(String(512), nullable=False)       # sub claim from IdP
    created_at = Column(DateTime(timezone=True), default=utcnow)

    user = relationship("UserAccount", back_populates="identities")


# ──────────────────────────────────────────────
# OPS & AUDIT
# ──────────────────────────────────────────────

class AuthSession(Base):
    """Active sessions. Platform owns these — revocable independently of IdP."""
    __tablename__ = "auth_session"

    session_id = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("user_account.user_id", ondelete="CASCADE"), nullable=False)
    tenant_id = Column(UUID(as_uuid=False), nullable=False)
    refresh_token_hash = Column(String(255), unique=True, nullable=False)
    is_revoked = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    expires_at = Column(DateTime(timezone=True), nullable=False)

    user = relationship("UserAccount", back_populates="sessions")


class LoginEvent(Base):
    """Append-only login audit trail."""
    __tablename__ = "login_event"

    id = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    tenant_id = Column(UUID(as_uuid=False), nullable=False)
    user_id = Column(UUID(as_uuid=False), nullable=True)    # null if user not found
    email = Column(String(255))
    auth_type = Column(String(16))                          # sso | password
    success = Column(Boolean, nullable=False)
    failure_reason = Column(String(255))
    ip_address = Column(String(64))
    created_at = Column(DateTime(timezone=True), default=utcnow)
