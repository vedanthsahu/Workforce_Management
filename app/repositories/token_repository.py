from datetime import datetime

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
