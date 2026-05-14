from __future__ import annotations

from typing import Any

from psycopg2.extras import RealDictCursor
from psycopg2.extensions import connection as PGConnection


def fetch_active_amenities(
    conn: PGConnection,
    *,
    tenant_id: str,
) -> list[dict[str, Any]]:

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT
                id::text AS id,
                amenity_key AS key,
                amenity_name AS name,
                category,
                description,
                icon_name AS icon
            FROM amenities
            WHERE tenant_id = %s
              AND is_active = true
            ORDER BY
                category,
                amenity_name
            """,
            (tenant_id,),
        )

        rows = cur.fetchall()

    return [dict(row) for row in rows]