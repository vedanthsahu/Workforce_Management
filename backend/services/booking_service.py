"""Service-layer booking workflows for day-based seat reservations."""

from __future__ import annotations

from datetime import date
from typing import Any

import psycopg2
from fastapi import HTTPException, status
from psycopg2 import errorcodes
from psycopg2.extensions import connection as PGConnection

from backend.repositories.booking_repository import (
    fetch_available_seats,
    fetch_bookings_for_user,
    fetch_seat_for_booking,
    has_active_booking_conflict,
    insert_booking,
)
from backend.repositories.user_repository import fetch_user_by_id
from backend.schemas.booking import AvailableSeatResponse, BookingResponse, CreateBookingRequest


def book_seat(
    conn: PGConnection,
    *,
    current_user: dict[str, Any],
    payload: CreateBookingRequest,
) -> BookingResponse:
    """Create one tenant-scoped booking and handle DB constraint failures."""
    tenant_id = str(current_user["tenant_id"])
    user_id = str(current_user["user_id"])

    try:
        target_user = fetch_user_by_id(conn, tenant_id=tenant_id, user_id=user_id)
        if target_user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "booking_user_not_found",
                    "message": "The booking user was not found in this tenant.",
                },
            )
        if target_user.get("status") != "ACTIVE":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "booking_user_inactive",
                    "message": "Bookings can only be created for ACTIVE users.",
                },
            )

        seat = fetch_seat_for_booking(
            conn,
            tenant_id=tenant_id,
            site_id=str(payload.site_id),
            building_id=str(payload.building_id),
            floor_id=str(payload.floor_id),
            seat_id=str(payload.seat_id),
        )
        if seat is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "booking_hierarchy_invalid",
                    "message": "The requested seat does not match the submitted site, building, floor, and tenant hierarchy.",
                },
            )
        if str(seat["tenant_id"]) != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "booking_seat_tenant_mismatch",
                    "message": "The requested seat does not belong to the authenticated tenant.",
                },
            )
        if seat.get("status") != "ACTIVE":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "booking_seat_inactive",
                    "message": "Bookings can only be created for ACTIVE seats.",
                },
            )
        if seat.get("is_bookable") is not True:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "booking_seat_not_bookable",
                    "message": "The requested seat is not bookable.",
                },
            )
        if has_active_booking_conflict(
            conn,
            tenant_id=tenant_id,
            seat_id=str(payload.seat_id),
            booking_date=payload.booking_date,
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "booking_conflict",
                    "message": "The requested seat already has an active booking for that day.",
                },
            )

        booking = insert_booking(
            conn,
            tenant_id=tenant_id,
            user_id=user_id,
            seat=seat,
            booking_date=payload.booking_date,
        )
        conn.commit()
    except HTTPException:
        conn.rollback()
        raise
    except ValueError as exc:
        conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "invalid_booking_value",
                "message": str(exc),
            },
        ) from exc
    except LookupError as exc:
        conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "booking_create_failed",
                "message": str(exc),
            },
        ) from exc
    except psycopg2.Error as exc:
        conn.rollback()
        if exc.pgcode in {errorcodes.UNIQUE_VIOLATION, errorcodes.EXCLUSION_VIOLATION}:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "booking_conflict",
                    "message": "The requested seat already has an active booking for that day.",
                },
            ) from exc
        if exc.pgcode == errorcodes.FOREIGN_KEY_VIOLATION:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "booking_reference_not_found",
                    "message": "Seat or user reference was not found for this tenant.",
                },
            ) from exc
        if exc.pgcode == errorcodes.CHECK_VIOLATION:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "invalid_booking_target",
                    "message": "Booking status or source channel violates the schema checks.",
                },
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "booking_create_failed",
                "message": "Failed to create booking.",
            },
        ) from exc

    return BookingResponse(**booking)


def get_user_bookings(
    conn: PGConnection,
    *,
    current_user: dict[str, Any],
) -> list[BookingResponse]:
    """List bookings visible to the authenticated user."""
    try:
        bookings = fetch_bookings_for_user(
            conn,
            tenant_id=str(current_user["tenant_id"]),
            user_id=str(current_user["user_id"]),
        )
    except psycopg2.Error as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "booking_lookup_failed",
                "message": "Failed to fetch bookings.",
            },
        ) from exc

    return [BookingResponse(**booking) for booking in bookings]


def get_available_seats(
    conn: PGConnection,
    *,
    tenant_id: str,
    floor_id: str,
    booking_date: date,
) -> list[AvailableSeatResponse]:
    """List seats available on one floor for one booking date."""
    try:
        seats = fetch_available_seats(
            conn,
            tenant_id=tenant_id,
            floor_id=floor_id,
            booking_date=booking_date,
        )
    except psycopg2.Error as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "available_seats_lookup_failed",
                "message": "Failed to fetch available seats.",
            },
        ) from exc

    return [AvailableSeatResponse(**seat) for seat in seats]
