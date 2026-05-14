"""
Dashboard.py for schema define
"""
from __future__ import annotations

from pydantic import BaseModel

from backend.schemas.auth import FavoriteSeatResponse


class DashboardMeResponse(BaseModel):
    favorite_seat: FavoriteSeatResponse | None = None

    days_in_office_total: int = 0
    days_in_office_current_month: int = 0
    days_in_office_current_year: int = 0

    team_rank_current_year: int | None = None
    team_member_count: int = 0