"""Service-layer location lookups.

This module wraps read-only repository functions for offices, floors, and
seats, translating database failures into HTTP-friendly exceptions.
"""

import psycopg2
from fastapi import HTTPException, status
from psycopg2.extensions import connection as PGConnection

from backend.repositories.location_repository import fetch_floors_by_office, fetch_offices, fetch_seats_by_floor
from backend.schemas.location import FloorResponse, OfficeResponse, SeatResponse


def get_offices(conn: PGConnection) -> list[OfficeResponse]:
    """Return all offices configured in the system.

    Args:
        conn: Open PostgreSQL connection.

    Returns:
        list[OfficeResponse]: Office response models.

    Side Effects:
        Executes a database read through the repository layer.

    Failure Modes:
        Raises ``HTTPException`` when office lookup fails.
    """
    try:
        offices = fetch_offices(conn)
    except psycopg2.Error as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch offices",
        ) from exc

    return [OfficeResponse(**office) for office in offices]


def get_floors_by_office(
    conn: PGConnection,
    *,
    office_id: str,
) -> list[FloorResponse]:
    """Return floors for a specific office.

    Args:
        conn: Open PostgreSQL connection.
        office_id: Office identifier used to filter floors.

    Returns:
        list[FloorResponse]: Floor response models for the office.

    Side Effects:
        Executes a database read through the repository layer.

    Failure Modes:
        Raises ``HTTPException`` when floor lookup fails.
    """
    try:
        floors = fetch_floors_by_office(conn, office_id=office_id)
    except psycopg2.Error as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch floors",
        ) from exc

    return [FloorResponse(**floor) for floor in floors]


def get_seats_by_floor(
    conn: PGConnection,
    *,
    floor_id: str,
) -> list[SeatResponse]:
    """Return seats configured for a floor.

    Args:
        conn: Open PostgreSQL connection.
        floor_id: Floor identifier used to filter seats.

    Returns:
        list[SeatResponse]: Seat response models for the floor.

    Side Effects:
        Executes a database read through the repository layer.

    Failure Modes:
        Raises ``HTTPException`` when seat lookup fails.
    """
    try:
        seats = fetch_seats_by_floor(conn, floor_id=floor_id)
    except psycopg2.Error as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch seats",
        ) from exc

    return [SeatResponse(**seat) for seat in seats]
