from datetime import datetime

from pydantic import BaseModel, Field, field_validator


def _normalize_email(value: str) -> str:
    return value.strip().lower()


def _validate_non_empty(value, field_name: str) -> str:
    if isinstance(value, int):
        normalized = str(value)
    elif isinstance(value, str):
        normalized = value.strip()
    else:
        raise TypeError(f"{field_name} must be str or int")
    if not normalized:
        raise ValueError(f"{field_name} cannot be empty")
    return normalized


class SignupRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: str
    password: str = Field(min_length=8, max_length=128)
    location: str = Field(min_length=1, max_length=100)
    project: int = Field(gt=0)
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

    @field_validator("location", "role")
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
