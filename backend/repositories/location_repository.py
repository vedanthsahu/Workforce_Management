from typing import Any

from psycopg2.extras import RealDictCursor
from psycopg2.extensions import connection as PGConnection


def fetch_offices(conn: PGConnection) -> list[dict[str, Any]]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT
                office_id::text AS office_id,
                name
            FROM offices
            """
        )
        rows = cur.fetchall()
    return [dict(row) for row in rows]


def fetch_floors_by_office(conn: PGConnection, *, office_id: str) -> list[dict[str, Any]]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT
                floor_id::text AS floor_id,
                office_id::text AS office_id,
                floor_number
            FROM floors
            WHERE office_id = %s
            """,
            (office_id,),
        )
        rows = cur.fetchall()
    return [dict(row) for row in rows]


def fetch_seats_by_floor(conn: PGConnection, *, floor_id: str) -> list[dict[str, Any]]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT
                seat_id::text AS seat_id,
                floor_id::text AS floor_id,
                seat_number,
                seat_type
            FROM seats
            WHERE floor_id = %s
            """,
            (floor_id,),
        )
        rows = cur.fetchall()
    return [dict(row) for row in rows]
