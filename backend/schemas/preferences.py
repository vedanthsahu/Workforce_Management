from __future__ import annotations

from pydantic import BaseModel


class AmenityResponse(BaseModel):
    id: str
    key: str
    name: str
    category: str | None = None
    description: str | None = None
    icon: str | None = None


class PreferencesResponse(BaseModel):
    amenities: list[AmenityResponse]