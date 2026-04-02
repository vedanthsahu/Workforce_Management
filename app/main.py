from fastapi import FastAPI

from app.api.routes.auth import router as auth_router
from app.db.connection import get_db_connection
from app.repositories.token_repository import ensure_revoked_tokens_table, purge_expired_revoked_tokens
from app.repositories.user_repository import ensure_user_profile_columns

app = FastAPI(title="Seat Booking Auth API")
app.include_router(auth_router)


@app.on_event("startup")
def startup() -> None:
    with get_db_connection() as conn:
        ensure_user_profile_columns(conn)
        ensure_revoked_tokens_table(conn)
        purge_expired_revoked_tokens(conn)
        conn.commit()


@app.get("/")
def index() -> dict[str, object]:
    return {
        "service": "seat-booking-auth",
        "docs": "/docs",
        "endpoints": ["POST /signup", "POST /login", "GET /me", "POST /logout", "GET /health"],
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
