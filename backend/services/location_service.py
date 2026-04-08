import psycopg2
from fastapi import HTTPException, status
from psycopg2.extensions import connection as PGConnection

from backend.repositories.location_repository import fetch_floors_by_office, fetch_offices, fetch_seats_by_floor
from backend.schemas.location import FloorResponse, OfficeResponse, SeatResponse


def get_offices(conn: PGConnection) -> list[OfficeResponse]:
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
    try:
        seats = fetch_seats_by_floor(conn, floor_id=floor_id)
    except psycopg2.Error as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch seats",
        ) from exc

    return [SeatResponse(**seat) for seat in seats]
