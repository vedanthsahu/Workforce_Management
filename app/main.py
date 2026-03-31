from fastapi import FastAPI

from app.routes import router

app = FastAPI(title="Seat Booking Auth API")
app.include_router(router)


@app.get("/")
def index() -> dict[str, object]:
    return {
        "service": "seat-booking-auth",
        "docs": "/docs",
        "endpoints": ["POST /signup", "POST /login", "GET /me", "GET /health"],
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
