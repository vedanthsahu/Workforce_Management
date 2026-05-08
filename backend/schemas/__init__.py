"""Pydantic schema package for authentication-related payloads.

This module re-exports commonly used authentication request and response
schemas so callers can import them from a single package entrypoint.
"""

from backend.schemas.auth import MessageResponse, UserResponse

__all__ = ["MessageResponse", "UserResponse"]
