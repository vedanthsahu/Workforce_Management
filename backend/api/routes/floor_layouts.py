"""
Routes for floor layout management.
"""

from __future__ import annotations

from typing import Any, Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile
from psycopg2.extensions import connection as PGConnection

from backend.api.deps import require_permission
from backend.core.storage import upload_svg_to_s3
from backend.db.connection import get_db
from backend.schemas.floor_layout import (
    UploadFloorLayoutResponse,
)
from backend.schemas.floor_layout import (
    CreateFloorLayoutRequest,
    FloorLayoutResponse,
)
from backend.services.floor_layout_service import (
    create_floor_layout,
)
router = APIRouter(
    prefix="/admin/floor-layouts",
    tags=["floor-layouts"],
)

@router.post(
    "",
    response_model=FloorLayoutResponse,
    status_code=201,
)
def create_floor_layout_route(
    payload: CreateFloorLayoutRequest,

    current_user: Annotated[
        dict[str, Any],
        Depends(require_permission("layout:upload")),
    ],

    conn: Annotated[PGConnection, Depends(get_db)],
) -> FloorLayoutResponse:

    return create_floor_layout(
        conn,
        current_user=current_user,
        payload=payload,
    )
@router.post(
    "/upload-svg",
    response_model=UploadFloorLayoutResponse,
)
def upload_floor_layout_svg(
    file: UploadFile = File(...),

    site_id: int = Form(gt=0),
    building_id: int = Form(gt=0),
    floor_id: int = Form(gt=0),

    current_user: Annotated[
        dict[str, Any],
        Depends(require_permission("layout:upload")),
    ] = None,

    conn: Annotated[PGConnection, Depends(get_db)] = None,
) -> UploadFloorLayoutResponse:

    object_url = upload_svg_to_s3(
        file=file,
        tenant_id=str(current_user["tenant_id"]),
        site_id=str(site_id),
        building_id=str(building_id),
        floor_id=str(floor_id),
    )

    return UploadFloorLayoutResponse(
        object_url=object_url,
    )