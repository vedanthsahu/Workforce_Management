from datetime import datetime
from typing import Any, Annotated

from fastapi import APIRouter, Depends, Query, status
from psycopg2.extensions import connection as PGConnection

from app.api.deps import get_auth_context
from app.db.connection import get_db
from app.schemas.booking import AvailableSeatResponse, BookingResponse, CreateBookingRequest
from app.services.booking_service import book_seat, get_available_seats, get_user_bookings

router = APIRouter(prefix="/bookings", tags=["bookings"], dependencies=[Depends(get_auth_context)])


@router.post("", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
def create_booking(
    payload: CreateBookingRequest,
    auth_context: Annotated[dict[str, Any], Depends(get_auth_context)],
    conn: Annotated[PGConnection, Depends(get_db)],
) -> BookingResponse:
    return book_seat(
        conn,
        user_id=auth_context["claims"]["user_id"],
        payload=payload,
    )


@router.get("", response_model=list[BookingResponse])
def fetch_bookings(
    auth_context: Annotated[dict[str, Any], Depends(get_auth_context)],
    conn: Annotated[PGConnection, Depends(get_db)],
) -> list[BookingResponse]:
    return get_user_bookings(conn, user_id=auth_context["claims"]["user_id"])


@router.get("/available", response_model=list[AvailableSeatResponse])
def available_seats(
    floor_id: Annotated[int, Query(gt=0)],
    start_time: datetime,
    end_time: datetime,
    conn: Annotated[PGConnection, Depends(get_db)],
) -> list[AvailableSeatResponse]:
    return get_available_seats(
        conn,
        floor_id=floor_id,
        start_time=start_time,
        end_time=end_time,
    )
