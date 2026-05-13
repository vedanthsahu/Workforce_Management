"""HTTP routes for authenticated booking operations."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from psycopg2.extensions import connection as PGConnection

from backend.api.deps import get_current_user
from backend.db.connection import get_db
from backend.schemas.booking import AvailableSeatResponse, BookingResponse, CreateBookingRequest, CancelBookingRequest, ModifyBookingRequest
from backend.services.booking_service import book_seat, get_available_seats, get_user_past_bookings,get_user_current_bookings,get_user_cancelled_bookings,get_user_future_bookings, cancel_booking_by_id, modify_booking

router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.post("", response_model=BookingResponse, status_code=201)
def create_booking(
    payload: CreateBookingRequest,
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    conn: Annotated[PGConnection, Depends(get_db)],
) -> BookingResponse:
    return book_seat(conn, current_user=current_user, payload=payload)


@router.get("/me/past", response_model=list[BookingResponse])
def fetch_my_bookings(
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    conn: Annotated[PGConnection, Depends(get_db)],
) -> list[BookingResponse]:
    return get_user_past_bookings(conn, current_user=current_user)

@router.get("/me/current", response_model=list[BookingResponse])
def fetch_my_bookings(
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    conn: Annotated[PGConnection, Depends(get_db)],
) -> list[BookingResponse]:
    return get_user_current_bookings(conn, current_user=current_user)

@router.get("/me/cancelled", response_model=list[BookingResponse])
def fetch_my_bookings(
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    conn: Annotated[PGConnection, Depends(get_db)],
) -> list[BookingResponse]:
    return get_user_cancelled_bookings(conn, current_user=current_user)

@router.get("/me/future", response_model=list[BookingResponse])
def fetch_my_bookings(
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    conn: Annotated[PGConnection, Depends(get_db)],
) -> list[BookingResponse]:
    return get_user_future_bookings(conn, current_user=current_user)


@router.get("/available", response_model=list[AvailableSeatResponse])
def available_seats(
    floor_id: Annotated[int, Query(gt=0)],
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    conn: Annotated[PGConnection, Depends(get_db)],
    booking_date: date | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
) -> list[AvailableSeatResponse]:
    resolved_booking_date = _resolve_booking_date(booking_date, start_time, end_time)
    return get_available_seats(
        conn,
        tenant_id=str(current_user["tenant_id"]),
        floor_id=str(floor_id),
        booking_date=resolved_booking_date,
    )
@router.post("/{booking_id}/cancel", response_model=BookingResponse)
def cancel_booking_route(
    booking_id: str,
    payload: CancelBookingRequest,
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    conn: Annotated[PGConnection, Depends(get_db)],
) -> BookingResponse:
    return cancel_booking_by_id(
        conn,
        current_user=current_user,
        booking_id=booking_id,
        cancellation_reason=payload.cancellation_reason,
    )
@router.post("/{booking_id}/modify", response_model=BookingResponse)
def modify_booking_route(
    booking_id: str,
    payload: ModifyBookingRequest,
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    conn: Annotated[PGConnection, Depends(get_db)],
) -> BookingResponse:
    return modify_booking(
        conn,
        current_user=current_user,
        booking_id=booking_id,
        payload=payload,
    )

def _resolve_booking_date(
    booking_date: date | None,
    start_time: datetime | None,
    end_time: datetime | None,
) -> date:
    if booking_date is not None:
        return booking_date
    if start_time is None or end_time is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "missing_booking_date",
                "message": "Provide booking_date or both start_time and end_time.",
            },
        )
    if start_time > end_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "invalid_booking_window",
                "message": "start_time must be earlier than end_time.",
            },
        )
    if start_time.date() != end_time.date():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "invalid_booking_window",
                "message": "Seat availability queries must stay within one day.",
            },
        )
    return start_time.date()
