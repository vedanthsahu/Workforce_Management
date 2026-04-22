import httpx
from fastapi import HTTPException
from urllib.parse import urlencode
from core.config import get_settings
from models.tables import IdentityProvider

settings = get_settings()

# In production, cache this per IdP and refresh periodically
_discovery_cache: dict = {}


async def fetch_oidc_discovery(discovery_url: str) -> dict:
    """Fetch and cache the IdP's OpenID configuration."""
    if discovery_url in _discovery_cache:
        return _discovery_cache[discovery_url]

    async with httpx.AsyncClient() as client:
        resp = await client.get(discovery_url, timeout=10)
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail="Failed to fetch IdP discovery document")
        config = resp.json()
        _discovery_cache[discovery_url] = config
        return config


def build_oidc_redirect_url(idp: IdentityProvider, state: str) -> str:
    """
    Build the authorization URL to redirect the user to the IdP.
    State param carries tenant_id + random nonce for CSRF protection.
    """
    if not idp.discovery_url:
        raise HTTPException(status_code=500, detail="OIDC discovery URL not configured for this tenant")

    # In production, fetch this dynamically from discovery_url
    # For dev/demo we build the URL pattern directly
    base_url = idp.discovery_url.replace("/.well-known/openid-configuration", "")

    # Google / standard OIDC authorization endpoint pattern
    auth_endpoint = f"{base_url}/o/oauth2/v2/auth" if "google" in base_url else f"{base_url}/authorize"

    callback_url = f"{settings.OIDC_CALLBACK_BASE_URL}/auth/sso/callback/oidc"

    params = {
        "client_id": idp.client_id,
        "response_type": "code",
        "scope": idp.scopes or "openid email profile",
        "redirect_uri": callback_url,
        "state": state,
        "nonce": state,      # reuse state as nonce for demo — use separate nonce in prod
    }

    return f"{auth_endpoint}?{urlencode(params)}"


async def exchange_code_for_tokens(idp: IdentityProvider, code: str) -> dict:
    """Exchange the auth code for tokens at the IdP's token endpoint."""
    callback_url = f"{settings.OIDC_CALLBACK_BASE_URL}/auth/sso/callback/oidc"

    # In prod, fetch token endpoint from discovery document
    base_url = idp.discovery_url.replace("/.well-known/openid-configuration", "")
    token_endpoint = f"{base_url}/token"

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            token_endpoint,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": callback_url,
                "client_id": idp.client_id,
                "client_secret": idp.client_secret,
            },
            timeout=15,
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail=f"IdP token exchange failed: {resp.text}")
        return resp.json()


def parse_id_token_claims(id_token: str) -> dict:
    """
    Decode IdP's ID token WITHOUT verification for demo.
    In production: verify signature using IdP's JWKS endpoint.
    """
    import base64, json
    parts = id_token.split(".")
    if len(parts) != 3:
        raise HTTPException(status_code=400, detail="Invalid ID token format")
    # Add padding
    payload = parts[1] + "=" * (-len(parts[1]) % 4)
    claims = json.loads(base64.urlsafe_b64decode(payload))
    return claims
