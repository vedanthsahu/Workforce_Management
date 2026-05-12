"""Booking repository functions scoped by tenant and aligned to bookings schema."""

from __future__ import annotations

from datetime import date
from typing import Any

from psycopg2.extras import RealDictCursor
from psycopg2.extensions import connection as PGConnection

SOURCE_CHANNELS = {"WEB", "MOBILE", "ADMIN", "API"}


def fetch_seat_for_booking(
    conn: PGConnection,
    *,
    tenant_id: str,
    site_id: str,
    building_id: str,
    floor_id: str,
    seat_id: str,
) -> dict[str, Any] | None:
    """Fetch a tenant-scoped seat matching the requested hierarchy."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT
                s.id::text AS seat_id,
                s.tenant_id::text AS tenant_id,
                s.site_id::text AS site_id,
                s.building_id::text AS building_id,
                s.floor_id::text AS floor_id,
                s.status,
                s.is_bookable
            FROM seats AS s
            WHERE s.id = %s
              AND s.floor_id = %s
              AND s.building_id = %s
              AND s.site_id = %s
              AND s.tenant_id = %s
            """,
            (seat_id, floor_id, building_id, site_id, tenant_id),
        )
        row = cur.fetchone()
    return dict(row) if row else None


def has_active_booking_conflict(
    conn: PGConnection,
    *,
    tenant_id: str,
    seat_id: str,
    booking_date: date,
) -> bool:
    """Return whether a seat is already actively booked for a date."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT 1
            FROM bookings
            WHERE tenant_id = %s
              AND seat_id = %s
              AND booking_date = %s
              AND booking_status IN ('CONFIRMED', 'CHECKED_IN')
            LIMIT 1
            """,
            (tenant_id, seat_id, booking_date),
        )
        return cur.fetchone() is not None


def insert_booking(
    conn: PGConnection,
    *,
    tenant_id: str,
    user_id: str,
    seat: dict[str, Any],
    booking_date: date,
    source_channel: str = "WEB",
) -> dict[str, Any]:
    """Insert a booking using hierarchy values derived from the seat row."""
    normalized_source = source_channel.strip().upper()
    if normalized_source not in SOURCE_CHANNELS:
        raise ValueError("source_channel is not allowed by chk_bookings_source.")

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            INSERT INTO bookings (
                tenant_id,
                user_id,
                seat_id,
                site_id,
                building_id,
                floor_id,
                booking_date,
                booking_status,
                source_channel
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'CONFIRMED', %s)
            RETURNING id::text AS booking_id
            """,
            (
                tenant_id,
                user_id,
                seat["seat_id"],
                seat["site_id"],
                seat["building_id"],
                seat["floor_id"],
                booking_date,
                normalized_source,
            ),
        )
        created = cur.fetchone()
    if created is None:
        raise LookupError("Booking insert did not return an id.")
    booking = fetch_booking_by_id(
        conn,
        tenant_id=tenant_id,
        booking_id=str(created["booking_id"]),
    )
    if booking is None:
        raise LookupError("Created booking could not be reloaded.")
    return booking


def fetch_booking_by_id(
    conn: PGConnection,
    *,
    tenant_id: str,
    booking_id: str,
) -> dict[str, Any] | None:
    """Fetch one tenant-scoped booking with location display fields."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT
                b.id::text AS booking_id,
                b.tenant_id::text AS tenant_id,
                b.user_id::text AS user_id,
                b.seat_id::text AS seat_id,
                b.site_id::text AS site_id,
                b.building_id::text AS building_id,
                b.floor_id::text AS floor_id,
                s.seat_code,
                si.site_name,
                bu.building_name,
                f.floor_name,
                b.booking_date,
                b.booking_status,
                b.source_channel,
                b.check_in_at,
                b.checked_out_at,
                b.cancelled_at,
                b.cancellation_reason,
                b.created_at,
                b.updated_at
            FROM bookings AS b
            JOIN seats AS s
                ON b.seat_id = s.id
               AND b.tenant_id = s.tenant_id
            JOIN floors AS f
                ON b.floor_id = f.id
               AND b.tenant_id = f.tenant_id
            JOIN buildings AS bu
                ON b.building_id = bu.id
               AND b.tenant_id = bu.tenant_id
            JOIN sites AS si
                ON b.site_id = si.id
               AND b.tenant_id = si.tenant_id
            WHERE b.id = %s
              AND b.tenant_id = %s
            """,
            (booking_id, tenant_id),
        )
        row = cur.fetchone()
    return dict(row) if row else None
def fetch_booking_by_id_for_update(
    conn: PGConnection,
    *,
    tenant_id: str,
    booking_id: str,
) -> dict[str, Any] | None:
    """Fetch one booking row and lock it for transactional mutation."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT
                b.id::text AS booking_id,
                b.tenant_id::text AS tenant_id,
                b.user_id::text AS user_id,
                b.seat_id::text AS seat_id,
                b.site_id::text AS site_id,
                b.building_id::text AS building_id,
                b.floor_id::text AS floor_id,
                b.booking_date,
                b.booking_status,
                b.cancelled_at,
                b.cancellation_reason
            FROM bookings AS b
            WHERE b.id = %s
              AND b.tenant_id = %s
            FOR UPDATE
            """,
            (booking_id, tenant_id),
        )

        row = cur.fetchone()

    return dict(row) if row else None
def cancel_booking(
    conn: PGConnection,
    *,
    tenant_id: str,
    booking_id: str,
    cancellation_reason: str,
) -> None:
    """Soft-cancel one booking."""
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE bookings
            SET
                booking_status = 'CANCELLED',
                cancelled_at = NOW(),
                cancellation_reason = %s,
                updated_at = NOW()
            WHERE id = %s
              AND tenant_id = %s
            """,
            (
                cancellation_reason,
                booking_id,
                tenant_id,
            ),
        )


def fetch_bookings_for_user(
    conn: PGConnection,
    *,
    tenant_id: str,
    user_id: str,
) -> list[dict[str, Any]]:
    return

def fetch_past_bookings_for_user(
    conn: PGConnection,
    *,
    tenant_id: str,
    user_id: str,
) -> list[dict[str, Any]]:
    """Fetch bookings for one user within one tenant."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT
                b.id::text AS booking_id,
                b.tenant_id::text AS tenant_id,
                b.user_id::text AS user_id,
                b.seat_id::text AS seat_id,
                b.site_id::text AS site_id,
                b.building_id::text AS building_id,
                b.floor_id::text AS floor_id,
                s.seat_code,
                si.site_name,
                bu.building_name,
                f.floor_name,
                b.booking_date,
                b.booking_status,
                b.source_channel,
                b.check_in_at,
                b.checked_out_at,
                b.cancelled_at,
                b.cancellation_reason,
                b.created_at,
                b.updated_at
            FROM bookings AS b
            JOIN seats AS s
                ON b.seat_id = s.id
               AND b.tenant_id = s.tenant_id
            JOIN floors AS f
                ON b.floor_id = f.id
               AND b.tenant_id = f.tenant_id
            JOIN buildings AS bu
                ON b.building_id = bu.id
               AND b.tenant_id = bu.tenant_id
            JOIN sites AS si
                ON b.site_id = si.id
               AND b.tenant_id = si.tenant_id
            WHERE b.user_id = %s
              AND b.tenant_id = %s
              AND b.booking_date < CURRENT_DATE
            ORDER BY b.booking_date DESC
            """,
            (user_id, tenant_id),
        )
        rows = cur.fetchall()
    return [dict(row) for row in rows]

def fetch_current_bookings_for_user(
    conn: PGConnection,
    *,
    tenant_id: str,
    user_id: str,
) -> list[dict[str, Any]]:
    """Fetch bookings for one user within one tenant."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT
                b.id::text AS booking_id,
                b.tenant_id::text AS tenant_id,
                b.user_id::text AS user_id,
                b.seat_id::text AS seat_id,
                b.site_id::text AS site_id,
                b.building_id::text AS building_id,
                b.floor_id::text AS floor_id,
                s.seat_code,
                si.site_name,
                bu.building_name,
                f.floor_name,
                b.booking_date,
                b.booking_status,
                b.source_channel,
                b.check_in_at,
                b.checked_out_at,
                b.cancelled_at,
                b.cancellation_reason,
                b.created_at,
                b.updated_at
            FROM bookings AS b
            JOIN seats AS s
                ON b.seat_id = s.id
               AND b.tenant_id = s.tenant_id
            JOIN floors AS f
                ON b.floor_id = f.id
               AND b.tenant_id = f.tenant_id
            JOIN buildings AS bu
                ON b.building_id = bu.id
               AND b.tenant_id = bu.tenant_id
            JOIN sites AS si
                ON b.site_id = si.id
               AND b.tenant_id = si.tenant_id
            WHERE b.user_id = %s
              AND b.tenant_id = %s
              AND b.booking_date = CURRENT_DATE
            ORDER BY b.booking_date DESC
            """,
            (user_id, tenant_id),
        )
        rows = cur.fetchall()
    return [dict(row) for row in rows]

def fetch_future_bookings_for_user(
    conn: PGConnection,
    *,
    tenant_id: str,
    user_id: str,
) -> list[dict[str, Any]]:
    """Fetch bookings for one user within one tenant."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT
                b.id::text AS booking_id,
                b.tenant_id::text AS tenant_id,
                b.user_id::text AS user_id,
                b.seat_id::text AS seat_id,
                b.site_id::text AS site_id,
                b.building_id::text AS building_id,
                b.floor_id::text AS floor_id,
                s.seat_code,
                si.site_name,
                bu.building_name,
                f.floor_name,
                b.booking_date,
                b.booking_status,
                b.source_channel,
                b.check_in_at,
                b.checked_out_at,
                b.cancelled_at,
                b.cancellation_reason,
                b.created_at,
                b.updated_at
            FROM bookings AS b
            JOIN seats AS s
                ON b.seat_id = s.id
               AND b.tenant_id = s.tenant_id
            JOIN floors AS f
                ON b.floor_id = f.id
               AND b.tenant_id = f.tenant_id
            JOIN buildings AS bu
                ON b.building_id = bu.id
               AND b.tenant_id = bu.tenant_id
            JOIN sites AS si
                ON b.site_id = si.id
               AND b.tenant_id = si.tenant_id
            WHERE b.user_id = %s
              AND b.tenant_id = %s
              AND b.booking_date > CURRENT_DATE
            ORDER BY b.booking_date DESC
            """,
            (user_id, tenant_id),
        )
        rows = cur.fetchall()
    return [dict(row) for row in rows]


def fetch_available_seats(
    conn: PGConnection,
    *,
    tenant_id: str,
    floor_id: str,
    booking_date: date,
) -> list[dict[str, Any]]:
    """Fetch active bookable seats not occupied by active bookings that day."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT
                s.id::text AS seat_id,
                s.tenant_id::text AS tenant_id,
                s.site_id::text AS site_id,
                s.building_id::text AS building_id,
                s.floor_id::text AS floor_id,
                s.seat_code,
                s.seat_type,
                s.seat_neighborhood,
                s.is_bookable,
                s.status
            FROM seats AS s
            WHERE s.tenant_id = %s
              AND s.floor_id = %s
              AND s.status = 'ACTIVE'
              AND s.is_bookable = TRUE
              AND NOT EXISTS (
                    SELECT 1
                    FROM bookings AS bkg
                    WHERE bkg.tenant_id = %s
                      AND bkg.seat_id = s.id
                      AND bkg.booking_date = %s
                      AND bkg.booking_status IN ('CONFIRMED', 'CHECKED_IN')
              )
            ORDER BY s.seat_code, s.id
            """,
            (tenant_id, floor_id, tenant_id, booking_date),
        )
        rows = cur.fetchall()
    return [dict(row) for row in rows]
