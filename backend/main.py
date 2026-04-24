from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.api.routes.auth import router as auth_router
from backend.api.routes.bookings import router as bookings_router
from backend.api.routes.locations import router as locations_router
from backend.api.routes.sso import router as sso_router
from backend.core.config import get_settings
from backend.db.connection import get_db_connection
from backend.repositories.token_repository import (
    ensure_sessions_table,
    ensure_refresh_tokens_table,
    ensure_revoked_tokens_table,
    purge_expired_sessions,
    purge_expired_refresh_tokens,
    purge_expired_revoked_tokens,
)
from backend.repositories.user_repository import ensure_user_profile_columns

settings = get_settings()

app = FastAPI(title="Seat Booking Auth API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)
app.include_router(sso_router)
app.include_router(bookings_router)
app.include_router(locations_router)


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        headers=exc.headers,
        content=_normalize_http_error(exc.detail),
    )


@app.on_event("startup")
def startup() -> None:
    with get_db_connection() as conn:
        ensure_user_profile_columns(conn)
        ensure_revoked_tokens_table(conn)
        ensure_refresh_tokens_table(conn)
        ensure_sessions_table(conn)
        purge_expired_revoked_tokens(conn)
        purge_expired_refresh_tokens(conn)
        purge_expired_sessions(conn, settings.session_ttl)
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
            "GET /auth/login",
            "GET /auth/callback",
            "GET /auth/me",
            "GET /auth/logout",
            "GET /graph/me",
            "GET /graph/groups",
            "GET /graph/manager",
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


def _normalize_http_error(detail: Any) -> dict[str, Any]:
    if isinstance(detail, dict):
        if "error" in detail and isinstance(detail["error"], dict):
            return detail

        payload: dict[str, Any] = {
            "error": {
                "code": str(detail.get("code") or "http_error"),
                "message": str(detail.get("message") or detail.get("detail") or "Request failed."),
            }
        }
        extra = {
            key: value
            for key, value in detail.items()
            if key not in {"code", "message", "detail"}
        }
        if extra:
            payload["error"]["details"] = extra
        return payload

    return {
        "error": {
            "code": "http_error",
            "message": str(detail),
        }
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
