from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from core.config import get_settings
from models.tables import Base, Tenant, TenantDomain, IdentityProvider, TenantPolicy

settings = get_settings()

engine = create_engine(settings.DATABASE_URL, echo=settings.DEBUG)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """FastAPI dependency — yields a DB session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables."""
    Base.metadata.create_all(bind=engine)


def seed_tenants(db: Session):
    """
    Seed the three demo tenants: test1.com, test2.com, test3.com.
    Each has a different IdP type to demonstrate config-driven routing.
    Safe to call multiple times — skips existing tenants.
    """
    tenants_config = [
        {
            "tenant_code": "test1",
            "tenant_name": "Test Corp One",
            "domain": "test1.com",
            "idp_type": "oidc",
            # Simulated OIDC — replace with real Okta/Azure/Google discovery URL
            "discovery_url": "https://accounts.google.com/.well-known/openid-configuration",
            "client_id": "test1-client-id",
            "client_secret": "test1-client-secret",
            "scopes": "openid email profile",
            "password_auth_allowed": False,   # SSO only
        },
        {
            "tenant_code": "test2",
            "tenant_name": "Test Corp Two",
            "domain": "test2.com",
            "idp_type": "oidc",
            # Simulated OIDC — replace with real Okta discovery URL
            "discovery_url": "https://dev-xxxx.okta.com/.well-known/openid-configuration",
            "client_id": "test2-client-id",
            "client_secret": "test2-client-secret",
            "scopes": "openid email profile groups",
            "password_auth_allowed": False,
        },
        {
            "tenant_code": "test3",
            "tenant_name": "Test Corp Three",
            "domain": "test3.com",
            "idp_type": "saml",
            # Simulated SAML — replace with real metadata URL
            "metadata_url": "https://test3-idp.example.com/metadata.xml",
            "entity_id": "https://test3-idp.example.com",
            "sso_url": "https://test3-idp.example.com/sso",
            "password_auth_allowed": True,    # Fallback allowed for test3
        },
    ]

    for cfg in tenants_config:
        existing = db.query(Tenant).filter_by(tenant_code=cfg["tenant_code"]).first()
        if existing:
            print(f"Tenant {cfg['tenant_code']} already exists — skipping")
            continue

        tenant = Tenant(tenant_code=cfg["tenant_code"], tenant_name=cfg["tenant_name"])
        db.add(tenant)
        db.flush()  # get tenant_id

        domain = TenantDomain(tenant_id=tenant.tenant_id, domain_name=cfg["domain"])
        db.add(domain)

        if cfg["idp_type"] == "oidc":
            idp = IdentityProvider(
                tenant_id=tenant.tenant_id,
                idp_type="oidc",
                discovery_url=cfg.get("discovery_url"),
                client_id=cfg.get("client_id"),
                client_secret=cfg.get("client_secret"),
                scopes=cfg.get("scopes", "openid email profile"),
            )
        else:
            idp = IdentityProvider(
                tenant_id=tenant.tenant_id,
                idp_type="saml",
                metadata_url=cfg.get("metadata_url"),
                entity_id=cfg.get("entity_id"),
                sso_url=cfg.get("sso_url"),
            )
        db.add(idp)

        policy = TenantPolicy(
            tenant_id=tenant.tenant_id,
            mfa_required=True,
            password_auth_allowed=cfg.get("password_auth_allowed", False),
        )
        db.add(policy)

        print(f"Seeded tenant: {cfg['tenant_name']} ({cfg['domain']})")

    db.commit()
