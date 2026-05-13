"""Pydantic schemas for day-based booking flows."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field


class CreateBookingRequest(BaseModel):
    """Request body for creating one seat booking for one day."""

    site_id: int = Field(gt=0)
    building_id: int = Field(gt=0)
    floor_id: int = Field(gt=0)
    seat_id: int = Field(gt=0)
    booking_date: date

class CancelBookingRequest(BaseModel):
    cancellation_reason: str | None = None

class ModifyBookingRequest(BaseModel):
    site_id: int = Field(gt=0)
    building_id: int = Field(gt=0)
    floor_id: int = Field(gt=0)
    seat_id: int = Field(gt=0)
    booking_date: date    

class BookingResponse(BaseModel):
    """Public representation of a booking returned by the API."""

    booking_id: str
    tenant_id: str
    user_id: str
    seat_id: str
    site_id: str | None = None
    building_id: str | None = None
    floor_id: str | None = None
    seat_code: str | None = None
    site_name: str | None = None
    building_name: str | None = None
    floor_name: str | None = None
    booking_date: date
    booking_status: str
    source_channel: str | None = None
    check_in_at: datetime | None = None
    checked_out_at: datetime | None = None
    cancelled_at: datetime | None = None
    cancellation_reason: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AvailableSeatResponse(BaseModel):
    """Public representation of an available seat."""

    seat_id: str
    tenant_id: str | None = None
    site_id: str | None = None
    building_id: str | None = None
    floor_id: str
    seat_code: str | None = None
    seat_type: str | None = None
    seat_neighborhood: str | None = None
    is_bookable: bool | None = None
    status: str | None = None
