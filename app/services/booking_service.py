from datetime import datetime, timezone

import psycopg2
from fastapi import HTTPException, status
from psycopg2 import errorcodes
from psycopg2.extensions import connection as PGConnection

from app.repositories.booking_repository import create_booking, fetch_available_seats, fetch_bookings_for_user
from app.schemas.booking import AvailableSeatResponse, BookingResponse, CreateBookingRequest


def _validate_booking_window(start_time: datetime, end_time: datetime) -> None:
    if start_time >= end_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_time must be earlier than end_time",
        )


def _derive_status(start_time: datetime, end_time: datetime, status_value: str) -> str:
    if status_value == "cancelled":
        return "cancelled"

    now = datetime.now(timezone.utc)
    normalized_start = start_time if start_time.tzinfo else start_time.replace(tzinfo=timezone.utc)
    normalized_end = end_time if end_time.tzinfo else end_time.replace(tzinfo=timezone.utc)

    if normalized_end <= now:
        return "completed"
    if normalized_start > now:
        return "upcoming"
    return "ongoing"


def book_seat(
    conn: PGConnection,
    *,
    user_id: str,
    payload: CreateBookingRequest,
) -> BookingResponse:
    _validate_booking_window(payload.start_time, payload.end_time)

    try:
        booking = create_booking(
            conn,
            seat_id=str(payload.seat_id),
            user_id=user_id,
            start_time=payload.start_time,
            end_time=payload.end_time,
        )
        conn.commit()
    except psycopg2.Error as exc:
        conn.rollback()
        if exc.pgcode == errorcodes.EXCLUSION_VIOLATION:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Seat is not available for the selected time window",
            ) from exc
        if exc.pgcode == errorcodes.FOREIGN_KEY_VIOLATION:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Seat not found",
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create booking",
        ) from exc

    booking["derived_status"] = _derive_status(
        booking["start_time"],
        booking["end_time"],
        booking["status"],
    )
    return BookingResponse(**booking)


def get_user_bookings(conn: PGConnection, *, user_id: str) -> list[BookingResponse]:
    try:
        bookings = fetch_bookings_for_user(conn, user_id=user_id)
    except psycopg2.Error as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch bookings",
        ) from exc

    return [BookingResponse(**booking) for booking in bookings]


def get_available_seats(
    conn: PGConnection,
    *,
    floor_id: int,
    start_time: datetime,
    end_time: datetime,
) -> list[AvailableSeatResponse]:
    _validate_booking_window(start_time, end_time)

    try:
        seats = fetch_available_seats(
            conn,
            floor_id=floor_id,
            start_time=start_time,
            end_time=end_time,
        )
    except psycopg2.Error as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch available seats",
        ) from exc

    return [AvailableSeatResponse(**seat) for seat in seats]
