from pydantic import BaseModel


class OfficeResponse(BaseModel):
    office_id: str
    name: str


class FloorResponse(BaseModel):
    floor_id: str
    office_id: str | None = None
    floor_number: int


class SeatResponse(BaseModel):
    seat_id: str
    floor_id: str | None = None
    seat_number: int
    seat_type: str | None = None
