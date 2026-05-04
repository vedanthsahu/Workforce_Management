"""Tenant-scoped location lookup repository functions."""

from __future__ import annotations

from typing import Any

from psycopg2.extras import RealDictCursor
from psycopg2.extensions import connection as PGConnection


def fetch_sites(conn: PGConnection, *, tenant_id: str) -> list[dict[str, Any]]:
    """Fetch active sites for one tenant."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT
                id::text AS site_id,
                site_code,
                site_name,
                city,
                country,
                timezone,
                address_line1,
                address_line2,
                status
            FROM sites
            WHERE tenant_id = %s
              AND status = 'ACTIVE'
            ORDER BY site_name, site_code, id
            """,
            (tenant_id,),
        )
        rows = cur.fetchall()
    return [dict(row) for row in rows]


def fetch_buildings_by_site(
    conn: PGConnection,
    *,
    tenant_id: str,
    site_id: str,
) -> list[dict[str, Any]]:
    """Fetch active buildings under one active tenant-scoped site."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT
                b.id::text AS building_id,
                b.site_id::text AS site_id,
                b.building_code,
                b.building_name,
                b.status
            FROM buildings AS b
            INNER JOIN sites AS s
                ON s.tenant_id = b.tenant_id
               AND s.id = b.site_id
            WHERE b.tenant_id = %s
              AND b.site_id = %s
              AND b.status = 'ACTIVE'
              AND s.status = 'ACTIVE'
            ORDER BY b.building_code, b.id
            """,
            (tenant_id, site_id),
        )
        rows = cur.fetchall()
    return [dict(row) for row in rows]


def fetch_floors_by_site(
    conn: PGConnection,
    *,
    tenant_id: str,
    site_id: str,
) -> list[dict[str, Any]]:
    """Fetch floors under all buildings for one tenant-scoped site."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT
                f.id::text AS floor_id,
                f.site_id::text AS site_id,
                f.building_id::text AS building_id,
                b.building_code,
                b.building_name,
                f.floor_code,
                f.floor_name,
                f.status
            FROM floors AS f
            JOIN buildings AS b
                ON f.building_id = b.id
               AND f.tenant_id = b.tenant_id
               AND f.site_id = b.site_id
            WHERE b.site_id = %s
              AND f.tenant_id = %s
            ORDER BY b.building_code, f.floor_code, f.id
            """,
            (site_id, tenant_id),
        )
        rows = cur.fetchall()
    return [dict(row) for row in rows]


def fetch_seats_by_floor(
    conn: PGConnection,
    *,
    tenant_id: str,
    floor_id: str,
) -> list[dict[str, Any]]:
    """Fetch seats configured for one tenant-scoped floor."""
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
            JOIN floors AS f
                ON s.floor_id = f.id
               AND s.tenant_id = f.tenant_id
               AND s.site_id = f.site_id
               AND s.building_id = f.building_id
            JOIN buildings AS b
                ON f.building_id = b.id
               AND f.tenant_id = b.tenant_id
               AND f.site_id = b.site_id
            JOIN sites AS si
                ON b.site_id = si.id
               AND b.tenant_id = si.tenant_id
            WHERE s.tenant_id = %s
              AND s.floor_id = %s
            ORDER BY s.seat_code, s.id
            """,
            (tenant_id, floor_id),
        )
        rows = cur.fetchall()
    return [dict(row) for row in rows]
