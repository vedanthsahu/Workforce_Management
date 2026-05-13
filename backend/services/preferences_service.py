from __future__ import annotations

import psycopg2
from fastapi import HTTPException, status
from psycopg2.extensions import connection as PGConnection

from backend.repositories.preferences_repository import (
    fetch_active_amenities,
)


def get_preferences(
    conn: PGConnection,
    *,
    tenant_id: str,
) -> dict:

    try:
        amenities = fetch_active_amenities(
            conn,
            tenant_id=tenant_id,
        )

        return {
            "amenities": amenities,
        }

    except psycopg2.Error as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "preferences_fetch_failed",
                "message": "Failed to fetch preferences.",
            },
        ) from exc