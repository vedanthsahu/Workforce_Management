"""This file is team_repository.py this is to get the user's team related info"""
from psycopg2.extras import RealDictCursor
from psycopg2.extensions import connection as PGConnection


def fetch_team_members_with_today_booking(
    conn: PGConnection,
    *,
    tenant_id: str,
    user_id: str,
) -> list[dict]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT 
                u.id::text AS user_id,
                u.full_name,
                u.email,

                t.id::text AS team_id,
                t.team_name,

                b.id::text AS booking_id,
                b.seat_id::text AS seat_id,

                s.seat_code,
                s.floor_id::text AS floor_id,
                s.building_id::text AS building_id,

                CASE WHEN b.id IS NOT NULL THEN TRUE ELSE FALSE END AS has_booking_today

            FROM team_members tm_target

            JOIN team_members tm
                ON tm.team_id = tm_target.team_id
                AND tm.tenant_id = tm_target.tenant_id

            JOIN app_users u
                ON u.id = tm.user_id
                AND u.tenant_id = tm.tenant_id

            JOIN teams t
                ON t.id = tm.team_id
                AND t.tenant_id = tm.tenant_id

            LEFT JOIN bookings b
                ON b.user_id = u.id
                AND b.tenant_id = u.tenant_id
                AND b.booking_date = CURRENT_DATE
                AND b.booking_status = 'CONFIRMED'

            LEFT JOIN seats s
                ON s.id = b.seat_id
                AND s.tenant_id = b.tenant_id

            WHERE tm_target.user_id = %s
              AND tm_target.tenant_id = %s
            """,
            (user_id, tenant_id),
        )

        rows = cur.fetchall()

    return [dict(row) for row in rows]