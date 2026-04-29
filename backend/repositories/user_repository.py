"""Repository helpers for user storage and SSO account linking.

This module manages user profile schema compatibility, user lookup queries,
standard user creation, and the upsert flow used to reconcile Microsoft SSO
identities with existing local accounts.
"""

from typing import Any
from datetime import datetime
import secrets
import uuid

from psycopg2.extras import RealDictCursor
from psycopg2.extensions import connection as PGConnection

from backend.core.security import hash_password

# Shared field list keeps all user queries aligned on the same public shape.
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
    """Ensure user-profile columns required by current code paths exist.

    Args:
        conn: Open PostgreSQL connection.

    Returns:
        None.

    Side Effects:
        Executes DDL statements that add profile and SSO-related columns or
        indexes. The caller is responsible for committing the transaction.

    Failure Modes:
        Propagates database execution errors raised by psycopg2.
    """
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
    """Fetch one user record by email address.

    Args:
        conn: Open PostgreSQL connection.
        email: Normalized email address to match.

    Returns:
        dict[str, Any] | None: User row including ``password_hash`` when found,
        otherwise ``None``.

    Side Effects:
        Executes a ``SELECT`` query against ``users``.

    Failure Modes:
        Propagates database execution errors raised by psycopg2.
    """
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
    """Fetch one user record by primary key.

    Args:
        conn: Open PostgreSQL connection.
        user_id: User identifier to match.

    Returns:
        dict[str, Any] | None: User row without password material, or ``None``
        if the user does not exist.

    Side Effects:
        Executes a ``SELECT`` query against ``users``.

    Failure Modes:
        Propagates database execution errors raised by psycopg2.
    """
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
    """Fetch one user record by Microsoft Entra object identifier.

    Args:
        conn: Open PostgreSQL connection.
        azure_oid: Stable Microsoft object identifier to match.

    Returns:
        dict[str, Any] | None: Matching user row, or ``None`` when no account is
        linked to the supplied identity.

    Side Effects:
        Executes a ``SELECT`` query against ``users``.

    Failure Modes:
        Propagates database execution errors raised by psycopg2.
    """
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
    """Normalize a user email address for consistent storage and lookup.

    Args:
        value: Raw email string supplied by a caller.

    Returns:
        str: Trimmed lowercase email string.

    Side Effects:
        None.

    Failure Modes:
        None. Structural validation is handled by the calling layer.
    """
    return value.strip().lower()


def _normalize_display_name(value: str | None) -> str | None:
    """Normalize an optional display name for user-profile persistence.

    Args:
        value: Optional display name supplied by Microsoft identity data.

    Returns:
        str | None: Trimmed display name, or ``None`` when the input is missing
        or blank.

    Side Effects:
        None.

    Failure Modes:
        None expected under normal runtime conditions.
    """
    if value is None:
        return None
    normalized = value.strip()
    return normalized if normalized else None


def _legacy_placeholder_password_hash() -> str:
    """Generate a placeholder password hash for SSO-provisioned users.

    Returns:
        str: Bcrypt hash of a random secret never shown to the user.

    Side Effects:
        Performs secure random generation and bcrypt hashing.

    Failure Modes:
        Propagates hashing errors from the shared security helper.
    """
    # SSO: Keep legacy login schema compatible for newly provisioned SSO users.
    return hash_password(secrets.token_urlsafe(32))


def upsert_user_from_sso(
    conn: PGConnection,
    *,
    azure_oid: str,
    email: str,
    display_name: str | None,
) -> dict[str, Any]:
    """Create or update a local user record from Microsoft SSO identity data.

    The lookup order favors the stable Azure object identifier and falls back to
    email-based linking for existing local accounts. New SSO-only users receive
    safe placeholder values for legacy required columns.

    Args:
        conn: Open PostgreSQL connection.
        azure_oid: Stable Microsoft object identifier for the account.
        email: Email address resolved from Microsoft claims or Graph.
        display_name: Optional display name resolved from Microsoft identity
            data.

    Returns:
        dict[str, Any]: Inserted or updated user row.

    Side Effects:
        Executes one or more ``SELECT``, ``UPDATE``, or ``INSERT`` statements
        against ``users``. Commit control remains with the caller.

    Failure Modes:
        Propagates database execution and constraint errors raised by psycopg2.
    """
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
    """Insert a local user account and return the created row.

    Args:
        conn: Open PostgreSQL connection.
        user_id: Application-generated user identifier.
        name: Display name for the user.
        email: Normalized email address.
        password_hash: Previously hashed password for local login.
        location: User location metadata.
        project: Numeric project identifier stored on the user profile.
        role: Role label stored on the user profile.

    Returns:
        dict[str, Any]: Inserted user row without password material.

    Side Effects:
        Executes an ``INSERT`` into ``users``. Commit control remains with the
        caller.

    Failure Modes:
        Propagates database execution and constraint errors raised by psycopg2.
    """
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
