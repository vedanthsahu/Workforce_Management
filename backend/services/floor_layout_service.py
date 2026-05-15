"""
Service layer for floor layout workflows.
"""

from __future__ import annotations

from typing import Any

import psycopg2
from fastapi import HTTPException, status
from psycopg2.extensions import connection as PGConnection

from backend.repositories.floor_layout_repository import (
    archive_existing_published_layout,
    fetch_floor_for_layout,
    get_next_layout_version,
    insert_floor_layout,
)
from backend.schemas.floor_layout import (
    CreateFloorLayoutRequest,
    FloorLayoutResponse,
)


def create_floor_layout(
    conn: PGConnection,
    *,
    current_user: dict[str, Any],
    payload: CreateFloorLayoutRequest,
) -> FloorLayoutResponse:

    tenant_id = str(current_user["tenant_id"])
    user_id = str(current_user["user_id"])

    try:
        floor = fetch_floor_for_layout(
            conn,
            tenant_id=tenant_id,
            site_id=str(payload.site_id),
            building_id=str(payload.building_id),
            floor_id=str(payload.floor_id),
        )

        if floor is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "invalid_floor_hierarchy",
                    "message": "Floor does not belong to provided hierarchy.",
                },
            )

        if payload.status == "PUBLISHED":
            archive_existing_published_layout(
                conn,
                tenant_id=tenant_id,
                floor_id=str(payload.floor_id),
            )

        version_no = get_next_layout_version(
            conn,
            tenant_id=tenant_id,
            floor_id=str(payload.floor_id),
        )

        created_layout = insert_floor_layout(
            conn,
            tenant_id=tenant_id,
            site_id=str(payload.site_id),
            building_id=str(payload.building_id),
            floor_id=str(payload.floor_id),
            layout_name=payload.layout_name,
            layout_file_url=payload.layout_file_url,
            version_no=version_no,
            status=payload.status,
            layout_metadata=payload.layout_metadata,
            uploaded_by_user_id=user_id,
        )

        conn.commit()

    except HTTPException:
        conn.rollback()
        raise

    except psycopg2.Error as exc:
        conn.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "floor_layout_create_failed",
                "message": "Failed to create floor layout.",
            },
        ) from exc

    return FloorLayoutResponse(**created_layout)