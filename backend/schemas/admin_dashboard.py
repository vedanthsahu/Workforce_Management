"""
Schemas for admin dashboard analytics responses.
"""

from __future__ import annotations

from pydantic import BaseModel


class AdminDashboardSummaryResponse(BaseModel):
    total_offices: int = 0
    total_floors: int = 0
    total_seats: int = 0

    booked_today: int = 0
    blocked_seats: int = 0

    occupancy_percentage: float = 0.0