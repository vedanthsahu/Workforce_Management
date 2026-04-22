# Seat Booking — Auth Service

Multi-tenant FastAPI authentication service supporting SSO (OIDC + SAML) and Email/Password with TOTP MFA.

---

## Project Structure

```
auth_app/
├── main.py                   # FastAPI app, lifespan, middleware
├── requirements.txt
├── .env.example
├── core/
│   ├── config.py             # Settings via pydantic-settings
│   ├── security.py           # JWT issue + decode
│   └── dependencies.py       # FastAPI auth dependencies
├── db/
│   └── database.py           # SQLAlchemy engine, session, seed data
├── models/
│   ├── tables.py             # All DB models (ORM)
│   └── schemas.py            # Pydantic request/response schemas
├── routers/
│   └── auth_router.py        # All /auth/* endpoints
└── services/
    ├── tenant_service.py     # Tenant discovery logic
    ├── auth_service.py       # Password, TOTP, sessions, audit
    └── oidc_service.py       # OIDC redirect + callback handling
```

---

## Quick Start

### 1. Prerequisites

- Python 3.11+
- PostgreSQL running locally (or update DATABASE_URL for SQLite in dev)

### 2. Install dependencies

```bash
cd auth_app
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env — set APP_SECRET_KEY and DATABASE_URL at minimum
```

### 4. Run the server

```bash
uvicorn main:app --reload --port 8000
```

On startup, the server will:
- Create all database tables automatically
- Seed the three demo tenants (test1.com, test2.com, test3.com)

### 5. Open the interactive docs

```
http://localhost:8000/docs      ← Swagger UI (try all endpoints here)
http://localhost:8000/redoc     ← ReDoc
```

---

## Demo Tenants

| Domain     | IdP Type | Password login | Notes                        |
|------------|----------|----------------|------------------------------|
| test1.com  | OIDC     | No             | Google-style OIDC (simulated)|
| test2.com  | OIDC     | No             | Okta-style OIDC (simulated)  |
| test3.com  | SAML     | Yes            | SAML + password fallback     |

---

## Connecting to Real IdPs

### OIDC (Okta, Azure AD, Google Workspace, Auth0)

Update the `identity_provider` row for the tenant in your DB:

| Field           | Where to get it                                              |
|-----------------|--------------------------------------------------------------|
| `discovery_url` | Your IdP's OpenID config URL (see below)                     |
| `client_id`     | From your IdP app registration                               |
| `client_secret` | From your IdP app registration                               |
| `scopes`        | Usually `openid email profile` — add `groups` if needed      |

**Discovery URLs by provider:**

```
Okta:            https://<your-domain>.okta.com/.well-known/openid-configuration
Azure AD:        https://login.microsoftonline.com/<tenant-id>/v2.0/.well-known/openid-configuration
Google:          https://accounts.google.com/.well-known/openid-configuration
Auth0:           https://<your-domain>.auth0.com/.well-known/openid-configuration
```

**Redirect URI to register in the IdP:**
```
http://localhost:8000/auth/sso/callback/oidc        (dev)
https://yourdomain.com/auth/sso/callback/oidc       (prod)
```

---

### SAML (Okta SAML, Azure AD SAML, ADFS, PingFederate)

Update the `identity_provider` row:

| Field          | Where to get it                              |
|----------------|----------------------------------------------|
| `metadata_url` | Your IdP's metadata XML URL                  |
| `entity_id`    | SP entity ID — usually your app URL          |
| `sso_url`      | IdP's SSO endpoint (from metadata)           |
| `certificate`  | x509 cert from IdP metadata                  |

**ACS (callback) URL to register with IdP:**
```
http://localhost:8000/auth/sso/callback/saml        (dev)
https://yourdomain.com/auth/sso/callback/saml       (prod)
```

> Note: Full SAML handler uses `python3-saml` library. The router slot is ready — implement `saml_service.py` following the same pattern as `oidc_service.py`.

---

## API Usage Guide

### Flow 1 — SSO Login (test1.com or test2.com)

**Step 1: Discover tenant**
```bash
curl -X POST http://localhost:8000/auth/discover \
  -H "Content-Type: application/json" \
  -d '{"email": "alice@test1.com"}'
```
Response:
```json
{
  "tenant_id": "uuid-here",
  "tenant_name": "Test Corp One",
  "domain": "test1.com",
  "sso_enabled": true,
  "idp_type": "oidc",
  "password_auth_allowed": false
}
```

**Step 2: Get SSO redirect URL**
```bash
curl -X POST http://localhost:8000/auth/sso/initiate \
  -H "Content-Type: application/json" \
  -d '{"email": "alice@test1.com"}'
```
Response:
```json
{
  "redirect_url": "https://accounts.google.com/o/oauth2/v2/auth?client_id=...&response_type=code&...",
  "idp_type": "oidc"
}
```

**Step 3:** Redirect browser to `redirect_url`. IdP authenticates. IdP calls `/auth/sso/callback/oidc?code=...&state=...` automatically.

**Step 4:** Callback returns tokens:
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 900
}
```

---

### Flow 2 — Password + TOTP Login (test3.com only)

**Step 1: Register**
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "bob@test3.com", "password": "StrongPass123!", "display_name": "Bob"}'
```
Response includes `totp_secret` and `qr_code_uri`. Open the URI in a QR generator or paste the secret into Google/Microsoft Authenticator.

**Step 2: Confirm MFA setup**
```bash
curl -X POST http://localhost:8000/auth/totp/confirm \
  -H "Content-Type: application/json" \
  -d '{"email": "bob@test3.com", "tenant_id": "<tenant-uuid>", "totp_code": "123456"}'
```

**Step 3: Login with password**
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "bob@test3.com", "password": "StrongPass123!"}'
```

**Step 4: Complete login with TOTP**
```bash
curl -X POST http://localhost:8000/auth/totp/verify \
  -H "Content-Type: application/json" \
  -d '{"email": "bob@test3.com", "tenant_id": "<tenant-uuid>", "totp_code": "456789"}'
```
Returns full `access_token` + `refresh_token`.

---

### Using the Access Token

```bash
curl http://localhost:8000/auth/me \
  -H "Authorization: Bearer <access_token>"
```

Response:
```json
{
  "user_id": "uuid",
  "email": "bob@test3.com",
  "tenant_id": "uuid",
  "role": "employee",
  "auth_type": "password"
}
```

---

### Refresh Tokens

```bash
curl -X POST http://localhost:8000/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "<refresh_token>"}'
```

---

### Logout

```bash
curl -X POST http://localhost:8000/auth/logout \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "<refresh_token>"}'
```

---

## Protecting Your Own Endpoints

```python
from fastapi import Depends
from core.dependencies import get_current_user, require_role

# Any authenticated user
@app.get("/seats")
def list_seats(current_user: dict = Depends(get_current_user)):
    tenant_id = current_user["tenant_id"]  # always scope queries by this
    ...

# Admin only
@app.post("/seats/assign")
def assign_seat(current_user: dict = Depends(require_role("admin", "superadmin"))):
    ...
```

---

## Production Checklist

- [ ] Set strong `APP_SECRET_KEY` (32+ random chars)
- [ ] Move `client_secret` and TOTP secrets to a vault (AWS Secrets Manager, HashiCorp Vault)
- [ ] Verify OIDC ID token signatures using IdP's JWKS endpoint (replace `parse_id_token_claims`)
- [ ] Restrict `CORS allow_origins` to your frontend domain
- [ ] Enable HTTPS — never run auth over plain HTTP
- [ ] Add rate limiting on `/auth/login` and `/auth/totp/verify`
- [ ] Set `DEBUG=false` in production
- [ ] Implement SAML handler for test3.com using `python3-saml`
- [ ] Add Redis for TOTP replay attack prevention (one code = one use)
- [ ] Schedule cleanup of expired `auth_session` rows
