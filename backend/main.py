from fastapi import FastAPI

from backend.api.routes.auth import router as auth_router
from backend.api.routes.bookings import router as bookings_router
from backend.api.routes.locations import router as locations_router
from backend.api.routes.sso import router as sso_router
from backend.db.connection import get_db_connection
from backend.repositories.token_repository import (
    ensure_refresh_tokens_table,
    ensure_revoked_tokens_table,
    purge_expired_refresh_tokens,
    purge_expired_revoked_tokens,
)
from backend.repositories.user_repository import ensure_user_profile_columns

app = FastAPI(title="Seat Booking Auth API")
app.include_router(auth_router)
# SSO: Cookie-based Microsoft login endpoints under /auth.
app.include_router(sso_router, prefix="/auth", tags=["SSO"])
app.include_router(bookings_router)
app.include_router(locations_router)


@app.on_event("startup")
def startup() -> None:
    with get_db_connection() as conn:
        ensure_user_profile_columns(conn)
        ensure_revoked_tokens_table(conn)
        ensure_refresh_tokens_table(conn)
        purge_expired_revoked_tokens(conn)
        purge_expired_refresh_tokens(conn)
        conn.commit()


@app.get("/")
def index() -> dict[str, object]:
    return {
        "service": "seat-booking-auth",
        "docs": "/docs",
        "endpoints": [
            "POST /signup",
            "POST /login",
            "POST /refresh",
            "GET /me",
            "POST /logout",
            "GET /auth/login-page",
            "GET /auth/callback",
            "GET /auth/session-check",
            "GET /auth/logout",
            "POST /bookings",
            "GET /bookings",
            "GET /bookings/available",
            "GET /offices",
            "GET /offices/{office_id}/floors",
            "GET /floors/{floor_id}/seats",
            "GET /health",
        ],
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
