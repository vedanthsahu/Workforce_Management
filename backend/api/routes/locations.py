from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from psycopg2.extensions import connection as PGConnection

from backend.api.deps import get_auth_context
from backend.db.connection import get_db
from backend.schemas.location import FloorResponse, OfficeResponse, SeatResponse
from backend.services.location_service import get_floors_by_office, get_offices, get_seats_by_floor

router = APIRouter(tags=["locations"], dependencies=[Depends(get_auth_context)])


@router.get("/offices", response_model=list[OfficeResponse])
def offices(conn: Annotated[PGConnection, Depends(get_db)]) -> list[OfficeResponse]:
    return get_offices(conn)


@router.get("/offices/{office_id}/floors", response_model=list[FloorResponse])
def floors_by_office(
    office_id: UUID,
    conn: Annotated[PGConnection, Depends(get_db)],
) -> list[FloorResponse]:
    return get_floors_by_office(conn, office_id=str(office_id))


@router.get("/floors/{floor_id}/seats", response_model=list[SeatResponse])
def seats_by_floor(
    floor_id: UUID,
    conn: Annotated[PGConnection, Depends(get_db)],
) -> list[SeatResponse]:
    return get_seats_by_floor(conn, floor_id=str(floor_id))
