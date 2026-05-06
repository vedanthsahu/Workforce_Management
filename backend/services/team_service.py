from typing import Any
from psycopg2.extensions import connection as PGConnection

from backend.repositories.team_repository import (
    fetch_team_members_with_today_booking,
)


def get_my_team_overview(
    conn: PGConnection,
    *,
    current_user: dict[str, Any],
):
    tenant_id = str(current_user["tenant_id"])
    user_id = str(current_user["user_id"])

    rows = fetch_team_members_with_today_booking(
        conn,
        tenant_id=tenant_id,
        user_id=user_id,
    )

    if not rows:
        return []

    team_map = {}

    for row in rows:
        team_id = row["team_id"]

        if team_id not in team_map:
            team_map[team_id] = {
                "team_id": team_id,
                "team_name": row["team_name"],
                "total_members": 0,
                "booked_today_count": 0,
                "members": [],
            }

        member = {
            "user_id": row["user_id"],
            "full_name": row["full_name"],
            "email": row["email"],
            "has_booking_today": row["has_booking_today"],
            "seat": None,
        }

        if row["has_booking_today"]:
            member["seat"] = {
                "seat_id": row["seat_id"],
                "seat_code": row["seat_code"],
                "floor_id": row["floor_id"],
                "building_id": row["building_id"],
            }
            team_map[team_id]["booked_today_count"] += 1

        team_map[team_id]["total_members"] += 1
        team_map[team_id]["members"].append(member)

    return list(team_map.values())