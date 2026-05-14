"""
Service layer for admin dashboard analytics.
"""

from __future__ import annotations

from datetime import date

import psycopg2
from fastapi import HTTPException, status
from psycopg2.extensions import connection as PGConnection

from backend.repositories.dashboard_repository import (
    fetch_admin_dashboard_summary,
)
from backend.schemas.admin_dashboard import (
    AdminDashboardSummaryResponse,
)


def get_admin_dashboard_summary(
    conn: PGConnection,
    *,
    tenant_id: str,
    selected_date: date,
    site_id: str | None = None,
    floor_id: str | None = None,
) -> AdminDashboardSummaryResponse:
    """
    Return aggregated admin dashboard metrics.
    """

    try:
        summary = fetch_admin_dashboard_summary(
            conn,
            tenant_id=tenant_id,
            selected_date=selected_date,
            site_id=site_id,
            floor_id=floor_id,
        )

    except psycopg2.Error as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "admin_dashboard_summary_failed",
                "message": "Failed to fetch admin dashboard summary.",
            },
        ) from exc

    return AdminDashboardSummaryResponse(**summary)