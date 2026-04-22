from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    APP_SECRET_KEY: str = "change-me-in-production-must-be-32-chars-minimum"
    APP_NAME: str = "SeatBookingAuth"
    DEBUG: bool = True

    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/seat_booking_auth"

    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    OIDC_CALLBACK_BASE_URL: str = "http://localhost:8000"

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
