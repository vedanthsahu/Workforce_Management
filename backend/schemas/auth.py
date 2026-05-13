"""Pydantic schemas for authentication endpoints."""

from __future__ import annotations
from datetime import datetime

from pydantic import BaseModel, model_validator

class MessageResponse(BaseModel):
    """Simple message-only response."""
    message: str

class FavoriteSeatResponse(BaseModel):
    seat_id: str
    seat_code: str
    booking_count: int

# class UserResponse(BaseModel):
#     """Public representation of a tenant-scoped authenticated user."""
   

#     user_id: str
#     tenant_id: str
#     tenant_id: str
#     email: str
#     full_name: str | None = None
#     display_name: str | None = None
#     name: str | None = None
#     microsoft_object_id: str | None = None
#     user_principal_name: str | None = None
#     mobile_phone: str | None = None
#     office_location: str | None = None
#     department: str | None = None
#     job_title: str | None = None
#     company_name: str | None = None
#     employee_id: str | None = None
#     manager_user_id: str | None = None
#     home_site_id: str | None = None
#     full_name: str | None = None
#     display_name: str | None = None
#     name: str | None = None
#     microsoft_object_id: str | None = None
#     user_principal_name: str | None = None
#     mobile_phone: str | None = None
#     office_location: str | None = None
#     department: str | None = None
#     job_title: str | None = None
#     company_name: str | None = None
#     employee_id: str | None = None
#     manager_user_id: str | None = None
#     role: str | None = None
#     status: str | None = None
#     graph_last_synced_at: datetime | None = None
#     status: str | None = None
#     graph_last_synced_at: datetime | None = None
#     created_at: datetime | None = None
#     updated_at: datetime | None = None
#     permissions: list 

#     @model_validator(mode="before")
#     @classmethod
#     def populate_compatibility_fields(cls, value):
#         if isinstance(value, dict):
#             payload = dict(value)
#             if payload.get("display_name") is None:
#                 payload["display_name"] = payload.get("full_name")
#             if payload.get("name") is None:
#                 payload["name"] = payload.get("display_name") or payload.get("full_name")
#             return payload
#         return value
class UserResponse(BaseModel):
    user_id: str
    tenant_id: str

    email: str

    full_name: str | None = None
    display_name: str | None = None
    name: str | None = None

    microsoft_object_id: str | None = None
    user_principal_name: str | None = None

    mobile_phone: str | None = None
    office_location: str | None = None

    department: str | None = None
    job_title: str | None = None
    company_name: str | None = None
    employee_id: str | None = None

    manager_user_id: str | None = None
    home_site_id: str | None = None

    role: str | None = None
    status: str | None = None

    graph_last_synced_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    permissions: list[str] = []

    @model_validator(mode="before")
    @classmethod
    def populate_compatibility_fields(cls, value):
        if isinstance(value, dict):
            payload = dict(value)

            if payload.get("display_name") is None:
                payload["display_name"] = payload.get("full_name")

            if payload.get("name") is None:
                payload["name"] = (
                    payload.get("display_name")
                    or payload.get("full_name")
                )

            return payload

        return value