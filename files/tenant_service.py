from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from models.tables import Tenant, TenantDomain, IdentityProvider, TenantPolicy


def extract_domain(email: str) -> str:
    """Extract domain from email — e.g. user@test1.com → test1.com"""
    return email.split("@")[-1].lower().strip()


def discover_tenant(email: str, db: Session) -> dict:
    """
    Step 1 of every login flow.
    Given an email, find the tenant, its IdP config, and its policy.
    Raises 404 if domain is not registered.
    """
    domain = extract_domain(email)

    tenant_domain = (
        db.query(TenantDomain)
        .filter_by(domain_name=domain, verified=True)
        .first()
    )
    if not tenant_domain:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No tenant registered for domain '{domain}'. Contact your administrator.",
        )

    tenant = db.query(Tenant).filter_by(tenant_id=tenant_domain.tenant_id).first()
    if not tenant or tenant.tenant_status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant is inactive or suspended.",
        )

    idp = (
        db.query(IdentityProvider)
        .filter_by(tenant_id=tenant.tenant_id, is_default=True)
        .first()
    )

    policy = db.query(TenantPolicy).filter_by(tenant_id=tenant.tenant_id).first()

    return {
        "tenant": tenant,
        "idp": idp,
        "policy": policy,
        "domain": domain,
    }


def get_tenant_by_id(tenant_id: str, db: Session) -> Tenant:
    tenant = db.query(Tenant).filter_by(tenant_id=tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant
