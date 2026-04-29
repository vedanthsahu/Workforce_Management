"""Pydantic schemas for office, floor, and seat responses.

These models define the public shapes returned by the location endpoints and
their corresponding service-layer helpers.
"""

from pydantic import BaseModel


class OfficeResponse(BaseModel):
    """Public representation of an office record."""

    office_id: str
    name: str


class FloorResponse(BaseModel):
    """Public representation of a floor within an office."""

    floor_id: str
    office_id: str | None = None
    floor_number: int


class SeatResponse(BaseModel):
    """Public representation of a seat on a floor."""

    seat_id: str
    floor_id: str | None = None
    seat_number: int
    seat_type: str | None = None
