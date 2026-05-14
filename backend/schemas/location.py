"""Pydantic schemas for location lookup responses."""

from __future__ import annotations

from pydantic import BaseModel


class SiteResponse(BaseModel):
    """Public representation of a site."""

    site_id: str
    site_code: str
    site_name: str
    city: str | None = None
    country: str | None = None
  


class BuildingResponse(BaseModel):
    """Public representation of a building within a site."""

    building_id: str
    site_id: str
    building_code: str
    building_name: str


class FloorResponse(BaseModel):
    """Public representation of a floor within a location/building."""

    floor_id: str
    site_id: str | None = None
    building_id: str | None = None
    building_code: str | None = None
    building_name: str | None = None
    floor_code: str | None = None
    floor_name: str | None = None


class SeatResponse(BaseModel):
    """Public representation of a seat on a floor."""

    seat_id: str
    tenant_id: str | None = None
    site_id: str | None = None
    building_id: str | None = None
    floor_id: str | None = None
    seat_code: str | None = None
    seat_type: str | None = None
    seat_neighborhood: str | None = None
    is_bookable: bool | None = None
    status: str | None = None
