"""HTTP routes for authenticated booking operations.

This module exposes endpoints to create bookings, list a user's bookings, and
query seat availability. All routes depend on resolved authentication context.
"""

from datetime import datetime
from typing import Any, Annotated

from fastapi import APIRouter, Depends, Query, status
from psycopg2.extensions import connection as PGConnection

from backend.api.deps import get_auth_context
from backend.db.connection import get_db
from backend.schemas.booking import AvailableSeatResponse, BookingResponse, CreateBookingRequest
from backend.services.booking_service import book_seat, get_available_seats, get_user_bookings

router = APIRouter(prefix="/bookings", tags=["bookings"], dependencies=[Depends(get_auth_context)])


@router.post("", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
def create_booking(
    payload: CreateBookingRequest,
    auth_context: Annotated[dict[str, Any], Depends(get_auth_context)],
    conn: Annotated[PGConnection, Depends(get_db)],
) -> BookingResponse:
    """Create a booking for the authenticated user.

    Args:
        payload: Validated booking request body.
        auth_context: Claims resolved by the authentication dependency.
        conn: Request-scoped PostgreSQL connection.

    Returns:
        BookingResponse: Created booking record.

    Side Effects:
        Delegates to the booking service, which performs validation and
        database writes.

    Failure Modes:
        Propagates ``HTTPException`` instances raised by the service layer.
    """
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
    """Return bookings owned by the authenticated user.

    Args:
        auth_context: Claims resolved by the authentication dependency.
        conn: Request-scoped PostgreSQL connection.

    Returns:
        list[BookingResponse]: Booking records for the current user.

    Side Effects:
        Delegates to the booking service for database reads.

    Failure Modes:
        Propagates ``HTTPException`` instances raised by the service layer.
    """
    return get_user_bookings(conn, user_id=auth_context["claims"]["user_id"])


@router.get("/available", response_model=list[AvailableSeatResponse])
def available_seats(
    floor_id: Annotated[int, Query(gt=0)],
    start_time: datetime,
    end_time: datetime,
    conn: Annotated[PGConnection, Depends(get_db)],
) -> list[AvailableSeatResponse]:
    """Return seats available on a floor for the requested time interval.

    Args:
        floor_id: Positive floor identifier provided as a query parameter.
        start_time: Requested booking start timestamp.
        end_time: Requested booking end timestamp.
        conn: Request-scoped PostgreSQL connection.

    Returns:
        list[AvailableSeatResponse]: Seats that are free for the interval.

    Side Effects:
        Delegates to the booking service for validation and database reads.

    Failure Modes:
        Propagates ``HTTPException`` instances raised by the service layer.
    """
    return get_available_seats(
        conn,
        floor_id=floor_id,
        start_time=start_time,
        end_time=end_time,
    )
