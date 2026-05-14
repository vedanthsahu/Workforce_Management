"""
Employee dashboard service to get the dashboard details for dashboard/me
"""

from __future__ import annotations

from typing import Any

import psycopg2
from fastapi import HTTPException, status
from psycopg2.extensions import connection as PGConnection

from backend.repositories.user_repository import (
    fetch_days_in_office,
    fetch_days_in_office_current_month,
    fetch_days_in_office_current_year,
    fetch_favorite_seat,
    fetch_team_rank_current_year,
)
from backend.schemas.dashboard import DashboardMeResponse


def get_dashboard_me(
    conn: PGConnection,
    *,
    current_user: dict[str, Any],
) -> DashboardMeResponse:
    try:
        favorite_seat = fetch_favorite_seat(
            conn,
            tenant_id=str(current_user["tenant_id"]),
            user_id=str(current_user["user_id"]),
        )

        days_in_office_total = fetch_days_in_office(
            conn,
            tenant_id=str(current_user["tenant_id"]),
            user_id=str(current_user["user_id"]),
        )

        days_in_office_current_month = (
            fetch_days_in_office_current_month(
                conn,
                tenant_id=str(current_user["tenant_id"]),
                user_id=str(current_user["user_id"]),
            )
        )

        days_in_office_current_year = (
            fetch_days_in_office_current_year(
                conn,
                tenant_id=str(current_user["tenant_id"]),
                user_id=str(current_user["user_id"]),
            )
        )

        rank_data = fetch_team_rank_current_year(
            conn,
            tenant_id=str(current_user["tenant_id"]),
            user_id=str(current_user["user_id"]),
        )
        favorite_seat = fetch_favorite_seat(
            conn,
            tenant_id=str(current_user["tenant_id"]),
            user_id=str(current_user["user_id"]),
        )

        days_in_office = fetch_days_in_office(
            conn,
            tenant_id=str(current_user["tenant_id"]),
            user_id=str(current_user["user_id"]),
        )

    except psycopg2.Error as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "dashboard_lookup_failed",
                "message": "Failed to load dashboard data.",
            },
        ) from exc

    return DashboardMeResponse(
    favorite_seat=favorite_seat,
    days_in_office_total=days_in_office_total,
    days_in_office_current_month=days_in_office_current_month,
    days_in_office_current_year=days_in_office_current_year,
    team_rank_current_year=rank_data["team_rank_current_year"],
    team_member_count=rank_data["team_member_count"],
)