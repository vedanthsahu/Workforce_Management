from fastapi import FastAPI

from app.api.routes.auth import router as auth_router
from app.api.routes.bookings import router as bookings_router
from app.db.connection import get_db_connection
from app.repositories.token_repository import (
    ensure_refresh_tokens_table,
    ensure_revoked_tokens_table,
    purge_expired_refresh_tokens,
    purge_expired_revoked_tokens,
)
from app.repositories.user_repository import ensure_user_profile_columns

app = FastAPI(title="Seat Booking Auth API")
app.include_router(auth_router)
app.include_router(bookings_router)


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
            "POST /bookings",
            "GET /bookings",
            "GET /bookings/available",
            "GET /health",
        ],
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
