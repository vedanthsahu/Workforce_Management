"""Booking-related repository functions.

This module contains the SQL queries used to create bookings, list a user's
bookings, and compute seat availability for a requested time window.
"""

from datetime import datetime
from typing import Any

from psycopg2.extras import RealDictCursor
from psycopg2.extensions import connection as PGConnection


def create_booking(
    conn: PGConnection,
    *,
    seat_id: str,
    user_id: str,
    start_time: datetime,
    end_time: datetime,
) -> dict[str, Any]:
    """Insert a confirmed booking row and return the created record.

    Args:
        conn: Open PostgreSQL connection.
        seat_id: Identifier of the seat being reserved.
        user_id: Identifier of the user creating the booking.
        start_time: Inclusive booking start timestamp.
        end_time: Exclusive booking end timestamp.

    Returns:
        dict[str, Any]: Created booking row normalized for API use.

    Side Effects:
        Executes an ``INSERT`` against the ``bookings`` table. Commit control is
        delegated to the caller.

    Failure Modes:
        Propagates database constraint and execution errors raised by psycopg2.
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            INSERT INTO bookings (
                seat_id,
                user_id,
                start_time,
                end_time,
                status
            )
            VALUES (%s, %s, %s, %s, 'confirmed')
            RETURNING
                booking_id::text AS booking_id,
                seat_id::text AS seat_id,
                user_id::text AS user_id,
                start_time,
                end_time,
                status,
                created_at
            """,
            (seat_id, user_id, start_time, end_time),
        )
        created = cur.fetchone()
    return dict(created)


def fetch_bookings_for_user(conn: PGConnection, *, user_id: str) -> list[dict[str, Any]]:
    """Fetch bookings owned by a user, newest first.

    Args:
        conn: Open PostgreSQL connection.
        user_id: Identifier of the user whose bookings should be returned.

    Returns:
        list[dict[str, Any]]: Booking rows enriched with a database-derived
        status label based on time and cancellation state.

    Side Effects:
        Executes a ``SELECT`` query against the ``bookings`` table.

    Failure Modes:
        Propagates database execution errors raised by psycopg2.
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT
                b.booking_id::text AS booking_id,
                b.seat_id::text AS seat_id,
                b.user_id::text AS user_id,
                b.start_time,
                b.end_time,
                b.status,
                b.created_at,
                CASE
                    WHEN b.status = 'cancelled' THEN 'cancelled'
                    WHEN b.end_time <= NOW() THEN 'completed'
                    WHEN b.start_time > NOW() THEN 'upcoming'
                    ELSE 'ongoing'
                END AS derived_status
            FROM bookings b
            WHERE b.user_id = %s
            ORDER BY b.start_time DESC
            """,
            (user_id,),
        )
        rows = cur.fetchall()
    return [dict(row) for row in rows]


def fetch_available_seats(
    conn: PGConnection,
    *,
    floor_id: int,
    start_time: datetime,
    end_time: datetime,
) -> list[dict[str, Any]]:
    """Fetch seats not blocked by bookings or seat blocks in a time window.

    Args:
        conn: Open PostgreSQL connection.
        floor_id: Numeric floor identifier used to scope the search.
        start_time: Inclusive start of the requested booking window.
        end_time: Exclusive end of the requested booking window.

    Returns:
        list[dict[str, Any]]: Seat records available for the entire interval.

    Side Effects:
        Executes a ``SELECT`` query that checks overlap against both
        ``bookings`` and ``seat_blocks``.

    Failure Modes:
        Propagates database execution errors raised by psycopg2.
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT
                s.seat_id::text AS seat_id,
                s.floor_id
            FROM seats s
            WHERE s.floor_id = %s
              AND NOT EXISTS (
                  SELECT 1
                  FROM bookings b
                  WHERE b.seat_id = s.seat_id
                    AND b.status <> 'cancelled'
                    AND tstzrange(b.start_time, b.end_time, '[)')
                        && tstzrange(%s, %s, '[)')
              )
              AND NOT EXISTS (
                  SELECT 1
                  FROM seat_blocks sb
                  WHERE sb.seat_id = s.seat_id
                    AND tstzrange(sb.start_time, sb.end_time, '[)')
                        && tstzrange(%s, %s, '[)')
              )
            ORDER BY s.seat_id
            """,
            (floor_id, start_time, end_time, start_time, end_time),
        )
        rows = cur.fetchall()
    return [dict(row) for row in rows]
