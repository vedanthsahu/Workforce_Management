from datetime import datetime, timedelta, timezone
import secrets
from typing import Any

from psycopg2.extras import RealDictCursor
from psycopg2.extensions import connection as PGConnection


def ensure_revoked_tokens_table(conn: PGConnection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS revoked_tokens (
                jti TEXT PRIMARY KEY,
                user_id UUID NOT NULL,
                expires_at TIMESTAMPTZ NOT NULL,
                revoked_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_revoked_tokens_expires_at
            ON revoked_tokens (expires_at)
            """
        )


def is_token_revoked(conn: PGConnection, jti: str) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM revoked_tokens WHERE jti = %s",
            (jti,),
        )
        return cur.fetchone() is not None


def revoke_token(
    conn: PGConnection,
    *,
    jti: str,
    user_id: str,
    expires_at: datetime,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO revoked_tokens (jti, user_id, expires_at)
            VALUES (%s, %s, %s)
            ON CONFLICT (jti) DO NOTHING
            """,
            (jti, user_id, expires_at),
        )


def purge_expired_revoked_tokens(conn: PGConnection) -> None:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM revoked_tokens WHERE expires_at <= NOW()")


def ensure_refresh_tokens_table(conn: PGConnection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS refresh_tokens (
                id UUID PRIMARY KEY,
                user_id UUID NOT NULL,
                token_hash TEXT NOT NULL UNIQUE,
                expires_at TIMESTAMPTZ NOT NULL,
                revoked BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                replaced_by_token_id UUID NULL,
                revoked_at TIMESTAMPTZ NULL
            )
            """
        )
        cur.execute(
            """
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_name = 'refresh_tokens'
                      AND column_name = 'token_id'
                ) AND NOT EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_name = 'refresh_tokens'
                      AND column_name = 'id'
                ) THEN
                    ALTER TABLE refresh_tokens RENAME COLUMN token_id TO id;
                END IF;
            END
            $$;
            """
        )
        cur.execute("ALTER TABLE refresh_tokens ADD COLUMN IF NOT EXISTS replaced_by_token_id UUID NULL")
        cur.execute("ALTER TABLE refresh_tokens ADD COLUMN IF NOT EXISTS revoked_at TIMESTAMPTZ NULL")
        cur.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_refresh_tokens_token_hash
            ON refresh_tokens (token_hash)
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user_id
            ON refresh_tokens (user_id)
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_refresh_tokens_expires_at
            ON refresh_tokens (expires_at)
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_refresh_tokens_replaced_by_token_id
            ON refresh_tokens (replaced_by_token_id)
            """
        )


def store_refresh_token(
    conn: PGConnection,
    *,
    token_id: str,
    user_id: str,
    token_hash: str,
    expires_at: datetime,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO refresh_tokens (
                id,
                user_id,
                token_hash,
                expires_at,
                revoked,
                replaced_by_token_id,
                revoked_at
            )
            VALUES (%s, %s, %s, %s, FALSE, NULL, NULL)
            """,
            (token_id, user_id, token_hash, expires_at),
        )


def fetch_refresh_token_by_hash(conn: PGConnection, token_hash: str) -> dict[str, Any] | None:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT
                id::text AS id,
                user_id::text AS user_id,
                token_hash,
                expires_at,
                revoked,
                created_at,
                replaced_by_token_id::text AS replaced_by_token_id,
                revoked_at
            FROM refresh_tokens
            WHERE token_hash = %s
            """,
            (token_hash,),
        )
        result = cur.fetchone()
    return dict(result) if result else None


def revoke_refresh_token(
    conn: PGConnection,
    *,
    token_id: str,
    replaced_by_token_id: str | None = None,
) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE refresh_tokens
            SET
                revoked = TRUE,
                revoked_at = NOW(),
                replaced_by_token_id = COALESCE(%s, replaced_by_token_id)
            WHERE id = %s
              AND revoked = FALSE
            """,
            (replaced_by_token_id, token_id),
        )
        return cur.rowcount > 0


def revoke_refresh_token_family(conn: PGConnection, *, token_id: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            WITH RECURSIVE token_chain AS (
                SELECT id, replaced_by_token_id
                FROM refresh_tokens
                WHERE id = %s

                UNION ALL

                SELECT child.id, child.replaced_by_token_id
                FROM refresh_tokens AS child
                INNER JOIN token_chain AS parent
                    ON parent.replaced_by_token_id = child.id
            )
            UPDATE refresh_tokens
            SET revoked = TRUE,
                revoked_at = COALESCE(revoked_at, NOW())
            WHERE id IN (SELECT id FROM token_chain)
            """,
            (token_id,),
        )


def purge_expired_refresh_tokens(conn: PGConnection) -> None:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM refresh_tokens WHERE expires_at <= NOW()")


def ensure_sessions_table(conn: PGConnection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS sso_sessions (
                session_token TEXT PRIMARY KEY,
                user_id UUID NOT NULL,
                email TEXT NOT NULL,
                access_token TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_sso_sessions_user_id
            ON sso_sessions (user_id)
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_sso_sessions_created_at
            ON sso_sessions (created_at)
            """
        )


def create_session(
    conn: PGConnection,
    *,
    user_id: str,
    email: str,
    access_token: str,
) -> dict[str, Any]:
    session_token = secrets.token_urlsafe(48)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            INSERT INTO sso_sessions (session_token, user_id, email, access_token)
            VALUES (%s, %s, %s, %s)
            RETURNING
                session_token,
                user_id::text AS user_id,
                email,
                access_token,
                created_at
            """,
            (session_token, user_id, email, access_token),
        )
        result = cur.fetchone()
    return dict(result)


def get_session(conn: PGConnection, session_token: str) -> dict[str, Any] | None:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT
                session_token,
                user_id::text AS user_id,
                email,
                access_token,
                created_at
            FROM sso_sessions
            WHERE session_token = %s
            """,
            (session_token,),
        )
        result = cur.fetchone()
    return dict(result) if result else None


def delete_session(conn: PGConnection, session_token: str) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            """
            DELETE FROM sso_sessions
            WHERE session_token = %s
            """,
            (session_token,),
        )
        return cur.rowcount > 0


def purge_expired_sessions(conn: PGConnection, session_ttl: int) -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=session_ttl)
    with conn.cursor() as cur:
        cur.execute(
            """
            DELETE FROM sso_sessions
            WHERE created_at <= %s
            """,
            (cutoff,),
        )
