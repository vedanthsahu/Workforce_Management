"""
Schemas for floor layout upload and persistence.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class UploadFloorLayoutResponse(BaseModel):
    object_url: str


class CreateFloorLayoutRequest(BaseModel):
    site_id: int = Field(gt=0)
    building_id: int = Field(gt=0)
    floor_id: int = Field(gt=0)

    layout_name: str = Field(min_length=1, max_length=255)

    layout_file_url: str

    status: str = Field(pattern="^(DRAFT|PUBLISHED)$")

    layout_metadata: dict[str, Any] | None = None


class FloorLayoutResponse(BaseModel):
    layout_id: str

    tenant_id: str

    site_id: str
    building_id: str
    floor_id: str

    layout_name: str
    layout_file_url: str

    file_storage_provider: str
    layout_type: str

    version_no: int

    is_published: bool

    layout_metadata: dict[str, Any] | None = None

    uploaded_by_user_id: str

    published_by_user_id: str | None = None

    published_at: datetime | None = None

    status: str

    created_at: datetime
    updated_at: datetime