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
