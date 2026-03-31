import os
from contextlib import contextmanager
from typing import Generator, Iterator

import psycopg2
from dotenv import load_dotenv
from psycopg2.extensions import connection as PGConnection

load_dotenv()


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _parse_int_env(name: str, default: str) -> int:
    raw_value = os.getenv(name, default)
    try:
        return int(raw_value)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer") from exc


def _build_db_config() -> dict[str, object]:
    return {
        "host": _require_env("DB_HOST"),
        "dbname": _require_env("DB_NAME"),
        "user": _require_env("DB_USER"),
        "password": _require_env("DB_PASSWORD"),
        "port": _parse_int_env("DB_PORT", "5432"),
        "sslmode": os.getenv("DB_SSLMODE", "require"),
        "connect_timeout": _parse_int_env("DB_CONNECT_TIMEOUT", "10"),
    }


@contextmanager
def get_db_connection() -> Iterator[PGConnection]:
    conn = psycopg2.connect(**_build_db_config())
    try:
        yield conn
    finally:
        conn.close()


def get_db() -> Generator[PGConnection, None, None]:
    with get_db_connection() as conn:
        yield conn
