from typing import Any
from datetime import datetime
import secrets
import uuid

from psycopg2.extras import RealDictCursor
from psycopg2.extensions import connection as PGConnection

from backend.core.security import hash_password

USER_SELECT_FIELDS = """
    user_id::text AS user_id,
    name,
    email,
    azure_oid,
    display_name,
    last_login,
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
        # SSO: Add Microsoft identity and profile fields.
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS azure_oid VARCHAR")
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS display_name VARCHAR")
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login TIMESTAMP")
        # SSO: Enforce unique non-null Azure OID values.
        cur.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_users_azure_oid_unique
            ON users (azure_oid)
            WHERE azure_oid IS NOT NULL
            """
        )


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


def fetch_user_by_azure_oid(conn: PGConnection, azure_oid: str) -> dict[str, Any] | None:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""
            SELECT {USER_SELECT_FIELDS}
            FROM users
            WHERE azure_oid = %s
            """,
            (azure_oid,),
        )
        result = cur.fetchone()
    return dict(result) if result else None


def _normalize_email(value: str) -> str:
    return value.strip().lower()


def _normalize_display_name(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized if normalized else None


def _legacy_placeholder_password_hash() -> str:
    # SSO: Keep legacy login schema compatible for newly provisioned SSO users.
    return hash_password(secrets.token_urlsafe(32))


def upsert_user_from_sso(
    conn: PGConnection,
    *,
    azure_oid: str,
    email: str,
    display_name: str | None,
) -> dict[str, Any]:
    normalized_email = _normalize_email(email)
    normalized_display_name = _normalize_display_name(display_name)
    now = datetime.utcnow()

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # SSO: Update existing account matched by stable Azure OID.
        cur.execute(
            f"""
            SELECT {USER_SELECT_FIELDS}
            FROM users
            WHERE azure_oid = %s
            """,
            (azure_oid,),
        )
        existing_by_oid = cur.fetchone()
        if existing_by_oid is not None:
            cur.execute(
                f"""
                UPDATE users
                SET
                    email = %s,
                    display_name = %s,
                    last_login = %s,
                    name = CASE WHEN %s IS NOT NULL THEN %s ELSE name END
                WHERE user_id = %s
                RETURNING {USER_SELECT_FIELDS}
                """,
                (
                    normalized_email,
                    normalized_display_name,
                    now,
                    normalized_display_name,
                    normalized_display_name,
                    existing_by_oid["user_id"],
                ),
            )
            return dict(cur.fetchone())

        # SSO: Link existing local account by email, then stamp Azure OID.
        cur.execute(
            f"""
            SELECT {USER_SELECT_FIELDS}
            FROM users
            WHERE email = %s
            """,
            (normalized_email,),
        )
        existing_by_email = cur.fetchone()
        if existing_by_email is not None:
            cur.execute(
                f"""
                UPDATE users
                SET
                    azure_oid = %s,
                    email = %s,
                    display_name = %s,
                    last_login = %s,
                    name = CASE WHEN %s IS NOT NULL THEN %s ELSE name END
                WHERE user_id = %s
                RETURNING {USER_SELECT_FIELDS}
                """,
                (
                    azure_oid,
                    normalized_email,
                    normalized_display_name,
                    now,
                    normalized_display_name,
                    normalized_display_name,
                    existing_by_email["user_id"],
                ),
            )
            return dict(cur.fetchone())

        # SSO: Provision new user with safe defaults for legacy required columns.
        generated_user_id = str(uuid.uuid4())
        fallback_name = normalized_email.split("@", 1)[0] or normalized_email
        resolved_name = normalized_display_name or fallback_name
        cur.execute(
            f"""
            INSERT INTO users (
                user_id,
                name,
                email,
                password_hash,
                location,
                project,
                role,
                azure_oid,
                display_name,
                last_login
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING {USER_SELECT_FIELDS}
            """,
            (
                generated_user_id,
                resolved_name,
                normalized_email,
                _legacy_placeholder_password_hash(),
                "N/A",
                0,
                "user",
                azure_oid,
                normalized_display_name,
                now,
            ),
        )
        return dict(cur.fetchone())


def create_user(
    conn: PGConnection,
    *,
    user_id: str,
    name: str,
    email: str,
    password_hash: str,
    location: str,
    project: int,
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
