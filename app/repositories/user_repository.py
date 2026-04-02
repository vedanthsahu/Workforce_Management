from typing import Any

from psycopg2.extras import RealDictCursor
from psycopg2.extensions import connection as PGConnection

USER_SELECT_FIELDS = """
    user_id::text AS user_id,
    name,
    email,
    location,
    project,
    role,
    created_at
"""


def ensure_user_profile_columns(conn: PGConnection) -> None:
    with conn.cursor() as cur:
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS location TEXT")
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS project TEXT")
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS role TEXT")


def fetch_user_by_email(conn: PGConnection, email: str) -> dict[str, Any] | None:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""
            SELECT {USER_SELECT_FIELDS}, password_hash
            FROM users
            WHERE email = %s
            """,
            (email,),
        )
        result = cur.fetchone()
    return dict(result) if result else None


def fetch_user_by_id(conn: PGConnection, user_id: str) -> dict[str, Any] | None:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""
            SELECT {USER_SELECT_FIELDS}
            FROM users
            WHERE user_id = %s
            """,
            (user_id,),
        )
        result = cur.fetchone()
    return dict(result) if result else None


def create_user(
    conn: PGConnection,
    *,
    user_id: str,
    name: str,
    email: str,
    password_hash: str,
    location: str,
    project: str,
    role: str,
) -> dict[str, Any]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""
            INSERT INTO users (
                user_id,
                name,
                email,
                password_hash,
                location,
                project,
                role
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING {USER_SELECT_FIELDS}
            """,
            (user_id, name, email, password_hash, location, project, role),
        )
        inserted = cur.fetchone()
    return dict(inserted)
