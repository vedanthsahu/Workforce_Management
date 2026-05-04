"""Service-layer location lookups scoped by tenant."""

from __future__ import annotations

import psycopg2
from fastapi import HTTPException, status
from psycopg2.extensions import connection as PGConnection

from backend.repositories.location_repository import (
    fetch_buildings_by_site,
    fetch_floors_by_site,
    fetch_seats_by_floor,
    fetch_sites,
)
from backend.schemas.location import BuildingResponse, FloorResponse, SeatResponse, SiteResponse


def get_sites(conn: PGConnection, *, tenant_id: str) -> list[SiteResponse]:
    """Return tenant-scoped active sites."""
    try:
        sites = fetch_sites(conn, tenant_id=tenant_id)
    except psycopg2.Error as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "site_lookup_failed",
                "message": "Failed to fetch sites.",
            },
        ) from exc

    return [SiteResponse(**site) for site in sites]


def get_buildings_by_site(
    conn: PGConnection,
    *,
    tenant_id: str,
    site_id: str,
) -> list[BuildingResponse]:
    """Return tenant-scoped active buildings for one site."""
    try:
        buildings = fetch_buildings_by_site(conn, tenant_id=tenant_id, site_id=site_id)
    except psycopg2.Error as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "building_lookup_failed",
                "message": "Failed to fetch buildings.",
            },
        ) from exc

    return [BuildingResponse(**building) for building in buildings]


def get_floors_by_site(
    conn: PGConnection,
    *,
    tenant_id: str,
    site_id: str,
) -> list[FloorResponse]:
    """Return tenant-scoped floors for one site through the full hierarchy."""
    try:
        floors = fetch_floors_by_site(conn, tenant_id=tenant_id, site_id=site_id)
    except psycopg2.Error as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "floor_lookup_failed",
                "message": "Failed to fetch floors.",
            },
        ) from exc

    return [FloorResponse(**floor) for floor in floors]


def get_seats_by_floor(
    conn: PGConnection,
    *,
    tenant_id: str,
    floor_id: str,
) -> list[SeatResponse]:
    """Return tenant-scoped seats for a floor."""
    try:
        seats = fetch_seats_by_floor(conn, tenant_id=tenant_id, floor_id=floor_id)
    except psycopg2.Error as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "seat_lookup_failed",
                "message": "Failed to fetch seats.",
            },
        ) from exc

    return [SeatResponse(**seat) for seat in seats]
