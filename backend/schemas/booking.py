"""Pydantic schemas for booking creation and availability lookups.

This module defines the request and response models used by booking endpoints
and by the service layer that formats booking and seat-availability data.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CreateBookingRequest(BaseModel):
    """Request body for creating a new booking."""

    seat_id: UUID
    start_time: datetime
    end_time: datetime


class BookingResponse(BaseModel):
    """Public representation of a booking returned by the API."""

    booking_id: str
    seat_id: str
    user_id: str
    start_time: datetime
    end_time: datetime
    status: str
    derived_status: str | None = None
    created_at: datetime | None = None


class AvailableSeatsQuery(BaseModel):
    """Query parameter model for seat-availability searches."""

    floor_id: int = Field(gt=0)
    start_time: datetime
    end_time: datetime


class AvailableSeatResponse(BaseModel):
    """Public representation of a seat that is free for a time window."""

    seat_id: str
    floor_id: int
