"""Pydantic schemas for local authentication payloads.

This module defines request and response models used by signup, login, logout,
and current-user endpoints together with shared input normalization helpers.
"""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


def _normalize_email(value: str) -> str:
    """Normalize an email address for validation and storage consistency.

    Args:
        value: Raw email value supplied by a client.

    Returns:
        str: Trimmed lowercase email string.

    Side Effects:
        None.

    Failure Modes:
        None. Structural validation happens in caller-specific validators.
    """
    return value.strip().lower()


def _validate_non_empty(value, field_name: str) -> str:
    """Normalize and reject empty string-like field values.

    Args:
        value: Candidate field value supplied by a client.
        field_name: Logical field name used in validation errors.

    Returns:
        str: Normalized string representation of the value.

    Side Effects:
        None.

    Failure Modes:
        Raises ``TypeError`` for unsupported input types and ``ValueError`` for
        empty values after normalization.
    """
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
    """Request body for local account registration."""

    name: str = Field(min_length=1, max_length=255)
    email: str
    password: str = Field(min_length=8, max_length=128)
    location: str = Field(min_length=1, max_length=100)
    project: int = Field(gt=0)
    role: str = Field(min_length=1, max_length=100)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        """Normalize and validate the signup display name.

        Args:
            value: Raw name value supplied in the signup payload.

        Returns:
            str: Trimmed non-empty name string.

        Side Effects:
            None.

        Failure Modes:
            Raises ``ValueError`` when the normalized value is empty.
        """
        return _validate_non_empty(value, "name")

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        """Normalize and validate the signup email address.

        Args:
            value: Raw email value supplied in the signup payload.

        Returns:
            str: Trimmed lowercase email string.

        Side Effects:
            None.

        Failure Modes:
            Raises ``ValueError`` when the normalized value does not resemble a
            basic email address.
        """
        normalized = _normalize_email(value)
        if "@" not in normalized or normalized.startswith("@") or normalized.endswith("@"):
            raise ValueError("Invalid email format")
        return normalized

    @field_validator("location", "role")
    @classmethod
    def validate_metadata(cls, value: str, info) -> str:
        """Normalize required signup metadata fields.

        Args:
            value: Raw metadata value supplied in the signup payload.
            info: Pydantic validation metadata containing the field name.

        Returns:
            str: Trimmed non-empty metadata value.

        Side Effects:
            None.

        Failure Modes:
            Raises ``ValueError`` when the normalized value is empty.
        """
        return _validate_non_empty(value, str(info.field_name))


class LoginRequest(BaseModel):
    """Request body for local email-and-password authentication."""

    email: str
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        """Normalize and validate the login email address.

        Args:
            value: Raw email value supplied in the login payload.

        Returns:
            str: Trimmed lowercase email string.

        Side Effects:
            None.

        Failure Modes:
            Raises ``ValueError`` when the normalized value does not resemble a
            basic email address.
        """
        normalized = _normalize_email(value)
        if "@" not in normalized or normalized.startswith("@") or normalized.endswith("@"):
            raise ValueError("Invalid email format")
        return normalized


class MessageResponse(BaseModel):
    """Simple response model for success messages without payload data."""

    message: str


class UserResponse(BaseModel):
    """Public representation of an authenticated or newly created user."""

    user_id: str
    name: str
    email: str
    location: str | None = None
    project: str | None = None
    role: str | None = None
    created_at: datetime | None = None
