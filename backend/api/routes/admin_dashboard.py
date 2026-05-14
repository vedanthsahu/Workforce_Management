"""
HTTP routes for admin dashboard analytics.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Annotated

from fastapi import APIRouter, Depends, Query
from psycopg2.extensions import connection as PGConnection

from backend.api.deps import (
    get_current_user,
    require_permission,
)
from backend.db.connection import get_db
from backend.schemas.admin_dashboard import (
    AdminDashboardSummaryResponse,
)
from backend.services.admin_dashboard_service import (
    get_admin_dashboard_summary,
)

router = APIRouter(
    prefix="/admin/dashboard",
    tags=["admin-dashboard"],
)


@router.get(
    "/summary",
    response_model=AdminDashboardSummaryResponse,
)
def admin_dashboard_summary(
    current_user: Annotated[
        dict[str, Any],
        Depends(require_permission("admin_dashboard:view")),
    ],
    conn: Annotated[PGConnection, Depends(get_db)],
    selected_date: Annotated[
        date | None,
        Query(alias="date"),
    ] = None,
    site_id: Annotated[
        int | None,
        Query(gt=0),
    ] = None,
    floor_id: Annotated[
        int | None,
        Query(gt=0),
    ] = None,
) -> AdminDashboardSummaryResponse:
    """
    Return aggregated admin dashboard summary metrics.
    """

    if selected_date is None:
        selected_date = date.today()

    return get_admin_dashboard_summary(
        conn,
        tenant_id=str(current_user["tenant_id"]),
        selected_date=selected_date,
        site_id=str(site_id) if site_id is not None else None,
        floor_id=str(floor_id) if floor_id is not None else None,
    )