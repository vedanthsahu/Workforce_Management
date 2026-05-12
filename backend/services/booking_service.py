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
    fetch_past_bookings_for_user,
    fetch_current_bookings_for_user,
    fetch_future_bookings_for_user,
    fetch_seat_for_booking,
    has_active_booking_conflict,
    insert_booking,
    cancel_booking,
    fetch_booking_by_id_for_update,
    fetch_booking_by_id,
)
from backend.repositories.user_repository import fetch_user_by_id
from backend.schemas.booking import AvailableSeatResponse, BookingResponse, CreateBookingRequest

def _can_manage_booking(
    *,
    current_user: dict[str, Any],
    booking_user: dict[str, Any],
) -> bool:
    """Return whether current user can mutate target user's bookings."""
    current_user_id = str(current_user["user_id"])
    current_role = str(current_user.get("role") or "")

    if current_user_id == str(booking_user["user_id"]):
        return True

    if booking_user.get("manager_user_id") == current_user_id:
        return True

    if current_role in {
        "OFFICE_ADMIN",
        "TENANT_ADMIN",
        "SUPPORT_ADMIN",
    }:
        return True

    return False

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


def get_user_past_bookings(
    conn: PGConnection,
    *,
    current_user: dict[str, Any],
) -> list[BookingResponse]:
    """List bookings visible to the authenticated user."""
    try:
        bookings = fetch_past_bookings_for_user(
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


def get_user_current_bookings(
    conn: PGConnection,
    *,
    current_user: dict[str, Any],
) -> list[BookingResponse]:
    """List bookings visible to the authenticated user."""
    try:
        bookings = fetch_current_bookings_for_user(
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


def get_user_future_bookings(
    conn: PGConnection,
    *,
    current_user: dict[str, Any],
) -> list[BookingResponse]:
    """List bookings visible to the authenticated user."""
    try:
        bookings = fetch_future_bookings_for_user(
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

def _can_manage_booking(
    *,
    current_user: dict[str, Any],
    booking_user: dict[str, Any],
) -> bool:
    current_user_id = str(current_user["user_id"])
    current_role = str(current_user.get("role") or "")

    if current_user_id == str(booking_user["user_id"]):
        return True

    if booking_user.get("manager_user_id") == current_user_id:
        return True

    if current_role in {
        "OFFICE_ADMIN",
        "TENANT_ADMIN",
        "SUPPORT_ADMIN",
    }:
        return True

    return False
def cancel_booking_by_id(
    conn: PGConnection,
    *,
    current_user: dict[str, Any],
    booking_id: str,
    cancellation_reason: str | None,
) -> BookingResponse:
    """Cancel one future booking using soft-cancellation."""
    tenant_id = str(current_user["tenant_id"])

    try:
        booking = fetch_booking_by_id_for_update(
            conn,
            tenant_id=tenant_id,
            booking_id=booking_id,
        )

        if booking is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "booking_not_found",
                    "message": "Booking was not found.",
                },
            )

        if booking["booking_date"] <= date.today():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "booking_not_mutable",
                    "message": "Only future bookings can be cancelled.",
                },
            )

        if booking["booking_status"] in {
            "CANCELLED",
            "COMPLETED",
            "NO_SHOW",
        }:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "booking_not_mutable",
                    "message": "This booking can no longer be modified.",
                },
            )

        booking_user = fetch_user_by_id(
            conn,
            tenant_id=tenant_id,
            user_id=str(booking["user_id"]),
        )

        if booking_user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "booking_user_not_found",
                    "message": "Booking owner was not found.",
                },
            )

        if not _can_manage_booking(
            current_user=current_user,
            booking_user=booking_user,
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "booking_forbidden",
                    "message": "You are not allowed to cancel this booking.",
                },
            )

        cancel_booking(
            conn,
            tenant_id=tenant_id,
            booking_id=booking_id,
            cancellation_reason=(
                cancellation_reason.strip()
                if cancellation_reason and cancellation_reason.strip()
                else "USER_CANCELLED"
            ),
        )

        conn.commit()

        updated_booking = fetch_booking_by_id(
            conn,
            tenant_id=tenant_id,
            booking_id=booking_id,
        )

        if updated_booking is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "code": "booking_reload_failed",
                    "message": "Failed to reload cancelled booking.",
                },
            )

        return BookingResponse(**updated_booking)

    except HTTPException:
        conn.rollback()
        raise

    except psycopg2.Error as exc:
        conn.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "booking_cancel_failed",
                "message": "Failed to cancel booking.",
            },
        ) from exc
def modify_booking(
    conn: PGConnection,
    *,
    current_user: dict[str, Any],
    booking_id: str,
    payload: ModifyBookingRequest,
) -> BookingResponse:
    """Modify a future booking by cancelling old booking and creating a new one."""
    tenant_id = str(current_user["tenant_id"])

    try:
        booking = fetch_booking_by_id_for_update(
            conn,
            tenant_id=tenant_id,
            booking_id=booking_id,
        )

        if booking is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "booking_not_found",
                    "message": "Booking was not found.",
                },
            )

        if booking["booking_date"] <= date.today():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "booking_not_mutable",
                    "message": "Only future bookings can be modified.",
                },
            )

        if booking["booking_status"] in {
            "CANCELLED",
            "CHECKED_IN",
            "COMPLETED",
            "NO_SHOW",
        }:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "booking_not_mutable",
                    "message": "This booking can no longer be modified.",
                },
            )

        booking_user = fetch_user_by_id(
            conn,
            tenant_id=tenant_id,
            user_id=str(booking["user_id"]),
        )

        if booking_user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "booking_user_not_found",
                    "message": "Booking owner was not found.",
                },
            )

        if not _can_manage_booking(
            current_user=current_user,
            booking_user=booking_user,
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "booking_forbidden",
                    "message": "You are not allowed to modify this booking.",
                },
            )

        if (
            str(booking["seat_id"]) == str(payload.seat_id)
            and booking["booking_date"] == payload.booking_date
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "booking_no_effect",
                    "message": "Modification request does not change booking details.",
                },
            )

        target_seat = fetch_seat_for_booking(
            conn,
            tenant_id=tenant_id,
            site_id=str(payload.site_id),
            building_id=str(payload.building_id),
            floor_id=str(payload.floor_id),
            seat_id=str(payload.seat_id),
        )

        if target_seat is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "booking_hierarchy_invalid",
                    "message": "The requested seat does not match the submitted hierarchy.",
                },
            )

        if target_seat.get("status") != "ACTIVE":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "booking_seat_inactive",
                    "message": "Bookings can only target ACTIVE seats.",
                },
            )

        if target_seat.get("is_bookable") is not True:
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
                    "message": "The requested seat already has an active booking.",
                },
            )

        cancel_booking(
            conn,
            tenant_id=tenant_id,
            booking_id=booking_id,
            cancellation_reason="MODIFIED",
        )

        new_booking = insert_booking(
            conn,
            tenant_id=tenant_id,
            user_id=str(booking["user_id"]),
            seat=target_seat,
            booking_date=payload.booking_date,
        )

        conn.commit()

        return BookingResponse(**new_booking)

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
                "code": "booking_modify_failed",
                "message": str(exc),
            },
        ) from exc

    except psycopg2.Error as exc:
        conn.rollback()

        if exc.pgcode in {
            errorcodes.UNIQUE_VIOLATION,
            errorcodes.EXCLUSION_VIOLATION,
        }:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "booking_conflict",
                    "message": "The requested seat already has an active booking.",
                },
            ) from exc

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "booking_modify_failed",
                "message": "Failed to modify booking.",
            },
        ) from exc