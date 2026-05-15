"""
Repository helpers for floor layout persistence.
"""
from __future__ import annotations
from psycopg2.extras import Json

from typing import Any

from psycopg2.extras import RealDictCursor
from psycopg2.extensions import connection as PGConnection


def fetch_floor_for_layout(
    conn: PGConnection,
    *,
    tenant_id: str,
    site_id: str,
    building_id: str,
    floor_id: str,
) -> dict[str, Any] | None:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT
                f.id::text AS floor_id,
                f.tenant_id::text AS tenant_id,
                f.site_id::text AS site_id,
                f.building_id::text AS building_id
            FROM floors AS f
            WHERE f.id = %s
              AND f.tenant_id = %s
              AND f.site_id = %s
              AND f.building_id = %s
            """,
            (
                floor_id,
                tenant_id,
                site_id,
                building_id,
            ),
        )

        row = cur.fetchone()

    return dict(row) if row else None


def archive_existing_published_layout(
    conn: PGConnection,
    *,
    tenant_id: str,
    floor_id: str,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE floor_layouts
            SET
                status = 'ARCHIVED',
                is_published = FALSE,
                updated_at = NOW()
            WHERE tenant_id = %s
              AND floor_id = %s
              AND status = 'PUBLISHED'
            """,
            (
                tenant_id,
                floor_id,
            ),
        )


def get_next_layout_version(
    conn: PGConnection,
    *,
    tenant_id: str,
    floor_id: str,
) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT COALESCE(MAX(version_no), 0)
            FROM floor_layouts
            WHERE tenant_id = %s
              AND floor_id = %s
            """,
            (
                tenant_id,
                floor_id,
            ),
        )

        row = cur.fetchone()

    current_version = int(row[0] or 0)

    return current_version + 1

def insert_floor_layout(
    conn: PGConnection,
    *,
    tenant_id: str,
    site_id: str,
    building_id: str,
    floor_id: str,
    layout_name: str,
    layout_file_url: str,
    version_no: int,
    status: str,
    layout_metadata: dict[str, Any] | None,
    uploaded_by_user_id: str,
) -> dict[str, Any]:

    is_published = status == "PUBLISHED"

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            INSERT INTO floor_layouts (
                tenant_id,
                site_id,
                building_id,
                floor_id,
                layout_name,
                layout_file_url,
                file_storage_provider,
                layout_type,
                version_no,
                is_published,
                layout_metadata,
                uploaded_by_user_id,
                published_by_user_id,
                published_at,
                status
            )
            VALUES (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                'S3',
                'SVG',
                %s,
                %s,
                %s,
                %s,
                %s,
                CASE
                    WHEN %s = 'PUBLISHED'
                    THEN NOW()
                    ELSE NULL
                END,
                %s
            )
            RETURNING
                id::text AS layout_id,
                tenant_id::text AS tenant_id,
                site_id::text AS site_id,
                building_id::text AS building_id,
                floor_id::text AS floor_id,
                layout_name,
                layout_file_url,
                file_storage_provider,
                layout_type,
                version_no,
                is_published,
                layout_metadata,
                uploaded_by_user_id::text AS uploaded_by_user_id,
                published_by_user_id::text AS published_by_user_id,
                published_at,
                status,
                created_at,
                updated_at
            """,
            (
                tenant_id,
                site_id,
                building_id,
                floor_id,
                layout_name,
                layout_file_url,
                version_no,
                is_published,
                Json(layout_metadata)
                if layout_metadata is not None
                else None,
                uploaded_by_user_id,
                uploaded_by_user_id if is_published else None,
                status,
                status,
            ),
        )

        row = cur.fetchone()

    if row is None:
        raise LookupError("Failed to create floor layout.")

    return dict(row)