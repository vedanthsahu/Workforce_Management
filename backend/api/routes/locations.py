"""HTTP routes for authenticated location and seat discovery."""

from __future__ import annotations

from typing import Any, Annotated

from fastapi import APIRouter, Depends, Path, Query
from psycopg2.extensions import connection as PGConnection

from backend.api.deps import get_current_user
from backend.db.connection import get_db
from backend.schemas.location import BuildingResponse, FloorResponse, SeatResponse, SiteResponse
from backend.services.location_service import (
    get_buildings_by_site,
    get_floors_by_site,
    get_seats_by_floor,
    get_sites,
)

router = APIRouter(tags=["locations"])


@router.get("/sites", response_model=list[SiteResponse])
def sites(
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    conn: Annotated[PGConnection, Depends(get_db)],
) -> list[SiteResponse]:
    return get_sites(conn, tenant_id=str(current_user["tenant_id"]))


@router.get("/buildings", response_model=list[BuildingResponse])
def buildings(
    site_id: Annotated[int, Query(gt=0)],
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    conn: Annotated[PGConnection, Depends(get_db)],
) -> list[BuildingResponse]:
    return get_buildings_by_site(
        conn,
        tenant_id=str(current_user["tenant_id"]),
        site_id=str(site_id),
    )


@router.get("/offices/{office_id}/floors", response_model=list[FloorResponse])
def floors_by_office(
    site_id: Annotated[int, Path(alias="office_id", gt=0)],
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    conn: Annotated[PGConnection, Depends(get_db)],
) -> list[FloorResponse]:
    return get_floors_by_site(
        conn,
        tenant_id=str(current_user["tenant_id"]),
        site_id=str(site_id),
    )


@router.get("/floors/{floor_id}/seats", response_model=list[SeatResponse])
def seats_by_floor(
    floor_id: Annotated[int, Path(gt=0)],
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    conn: Annotated[PGConnection, Depends(get_db)],
) -> list[SeatResponse]:
    return get_seats_by_floor(
        conn,
        tenant_id=str(current_user["tenant_id"]),
        floor_id=str(floor_id),
    )
