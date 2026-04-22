from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from core.config import get_settings
from db.database import init_db, seed_tenants, SessionLocal
from routers.auth_router import router as auth_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Initialising database...")
    init_db()
    db = SessionLocal()
    try:
        seed_tenants(db)
    finally:
        db.close()
    print("Ready.")
    yield
    # Shutdown (nothing to clean up for now)


app = FastAPI(
    title="Seat Booking — Auth Service",
    description="""
## Multi-tenant authentication service

Supports **SSO (OIDC + SAML)** and **Email/Password + TOTP MFA**.

### Demo tenants
| Domain | IdP Type | Password allowed |
|---|---|---|
| test1.com | OIDC (Google-style) | No — SSO only |
| test2.com | OIDC (Okta-style) | No — SSO only |
| test3.com | SAML | Yes — fallback allowed |

### Typical flows

**SSO flow:**
1. `POST /auth/discover` → get tenant + IdP info
2. `POST /auth/sso/initiate` → get redirect URL
3. Browser redirects to IdP → IdP calls `GET /auth/sso/callback/oidc`
4. Receive `access_token` + `refresh_token`

**Password + MFA flow:**
1. `POST /auth/discover` → confirm password is allowed
2. `POST /auth/register` → get TOTP secret + QR URI
3. Scan QR in Google/Microsoft Authenticator
4. `POST /auth/totp/confirm` → activate MFA
5. `POST /auth/login` → verify password
6. `POST /auth/totp/verify` → verify 6-digit code → receive tokens

**Token management:**
- `POST /auth/refresh` → rotate tokens
- `POST /auth/logout` → revoke session
- `GET /auth/me` → validate token + get current user
    """,
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # Restrict to your frontend domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok", "service": settings.APP_NAME}
