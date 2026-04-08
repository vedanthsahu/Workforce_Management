from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CreateBookingRequest(BaseModel):
    seat_id: UUID
    start_time: datetime
    end_time: datetime


class BookingResponse(BaseModel):
    booking_id: str
    seat_id: str
    user_id: str
    start_time: datetime
    end_time: datetime
    status: str
    derived_status: str | None = None
    created_at: datetime | None = None


class AvailableSeatsQuery(BaseModel):
    floor_id: int = Field(gt=0)
    start_time: datetime
    end_time: datetime


class AvailableSeatResponse(BaseModel):
    seat_id: str
    floor_id: int
