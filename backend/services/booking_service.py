"""Service-layer booking workflows.

This module applies booking-specific validation and error translation around
repository calls that create reservations, list user bookings, and compute seat
availability.
"""

from datetime import datetime, timezone

import psycopg2
from fastapi import HTTPException, status
from psycopg2 import errorcodes
from psycopg2.extensions import connection as PGConnection

from backend.repositories.booking_repository import create_booking, fetch_available_seats, fetch_bookings_for_user
from backend.schemas.booking import AvailableSeatResponse, BookingResponse, CreateBookingRequest


def _validate_booking_window(start_time: datetime, end_time: datetime) -> None:
    """Ensure a booking window is chronologically valid.

    Args:
        start_time: Requested booking start timestamp.
        end_time: Requested booking end timestamp.

    Returns:
        None.

    Side Effects:
        None.

    Failure Modes:
        Raises ``HTTPException`` when the interval is empty or reversed.
    """
    if start_time >= end_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_time must be earlier than end_time",
        )


def _derive_status(start_time: datetime, end_time: datetime, status_value: str) -> str:
    """Derive a user-facing booking status from persisted timestamps.

    Args:
        start_time: Booking start timestamp.
        end_time: Booking end timestamp.
        status_value: Stored booking status from the database.

    Returns:
        str: One of ``cancelled``, ``completed``, ``upcoming``, or ``ongoing``.

    Side Effects:
        Reads the current UTC time.

    Failure Modes:
        None. Naive datetimes are assumed to be UTC.
    """
    if status_value == "cancelled":
        return "cancelled"

    now = datetime.now(timezone.utc)
    # Normalize naive timestamps so derived-status logic behaves consistently
    # even if legacy rows were stored without explicit timezone metadata.
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
    """Create a booking for the authenticated user.

    Args:
        conn: Open PostgreSQL connection.
        user_id: Authenticated user identifier.
        payload: Validated booking request payload.

    Returns:
        BookingResponse: Created booking enriched with a derived status.

    Side Effects:
        Inserts a booking row and commits or rolls back the transaction.

    Failure Modes:
        Raises ``HTTPException`` for invalid windows, overlapping bookings,
        missing seat references, or database failures.
    """
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
    """List bookings belonging to one user.

    Args:
        conn: Open PostgreSQL connection.
        user_id: Authenticated user identifier.

    Returns:
        list[BookingResponse]: Booking response models for the user.

    Side Effects:
        Executes a database read through the repository layer.

    Failure Modes:
        Raises ``HTTPException`` when the repository query fails.
    """
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
    """List seats that can be booked for a requested interval.

    Args:
        conn: Open PostgreSQL connection.
        floor_id: Numeric floor identifier to search within.
        start_time: Requested booking start timestamp.
        end_time: Requested booking end timestamp.

    Returns:
        list[AvailableSeatResponse]: Available seat records for the interval.

    Side Effects:
        Executes a database read through the repository layer.

    Failure Modes:
        Raises ``HTTPException`` for invalid windows or database failures.
    """
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
