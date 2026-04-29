"""Location lookup repository functions.

This module exposes read-only queries for offices, floors, and seats so the
service layer can retrieve location metadata without embedding SQL.
"""

from typing import Any

from psycopg2.extras import RealDictCursor
from psycopg2.extensions import connection as PGConnection


def fetch_offices(conn: PGConnection) -> list[dict[str, Any]]:
    """Fetch all offices available in the system.

    Args:
        conn: Open PostgreSQL connection.

    Returns:
        list[dict[str, Any]]: Office rows normalized to string identifiers.

    Side Effects:
        Executes a ``SELECT`` query against the ``offices`` table.

    Failure Modes:
        Propagates database execution errors raised by psycopg2.
    """
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
    """Fetch floor records belonging to one office.

    Args:
        conn: Open PostgreSQL connection.
        office_id: Office identifier used to filter the result set.

    Returns:
        list[dict[str, Any]]: Floor rows associated with the requested office.

    Side Effects:
        Executes a ``SELECT`` query against the ``floors`` table.

    Failure Modes:
        Propagates database execution errors raised by psycopg2.
    """
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
    """Fetch seats configured for a floor.

    Args:
        conn: Open PostgreSQL connection.
        floor_id: Floor identifier used to filter the result set.

    Returns:
        list[dict[str, Any]]: Seat rows belonging to the requested floor.

    Side Effects:
        Executes a ``SELECT`` query against the ``seats`` table.

    Failure Modes:
        Propagates database execution errors raised by psycopg2.
    """
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
