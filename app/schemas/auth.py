from datetime import datetime

from pydantic import BaseModel, Field, field_validator


def _normalize_email(value: str) -> str:
    return value.strip().lower()


def _validate_non_empty(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} cannot be empty")
    return normalized


class SignupRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: str
    password: str = Field(min_length=8, max_length=128)
    location: str = Field(min_length=1, max_length=100)
    project: str = Field(min_length=1, max_length=100)
    role: str = Field(min_length=1, max_length=100)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return _validate_non_empty(value, "name")

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized = _normalize_email(value)
        if "@" not in normalized or normalized.startswith("@") or normalized.endswith("@"):
            raise ValueError("Invalid email format")
        return normalized

    @field_validator("location", "project", "role")
    @classmethod
    def validate_metadata(cls, value: str, info) -> str:
        return _validate_non_empty(value, str(info.field_name))


class LoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized = _normalize_email(value)
        if "@" not in normalized or normalized.startswith("@") or normalized.endswith("@"):
            raise ValueError("Invalid email format")
        return normalized


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MessageResponse(BaseModel):
    message: str


class UserResponse(BaseModel):
    user_id: str
    name: str
    email: str
    location: str | None = None
    project: str | None = None
    role: str | None = None
    created_at: datetime | None = None
