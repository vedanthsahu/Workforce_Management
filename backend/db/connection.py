"""Database connection helpers for PostgreSQL access.
connections.py
This module provides the low-level connection context manager used throughout
the backend and the FastAPI dependency wrapper that yields one connection per
request scope.
"""

from contextlib import contextmanager
from typing import Generator, Iterator

import psycopg2
from psycopg2.extensions import connection as PGConnection

from backend.core.config import get_settings


@contextmanager
def get_db_connection() -> Iterator[PGConnection]:
    """Open a PostgreSQL connection and ensure it is closed afterwards.

    Returns:
        Iterator[PGConnection]: Context-managed database connection.

    Side Effects:
        Establishes a new network connection to PostgreSQL and closes it on
        exit. Transaction commit and rollback decisions are left to callers.

    Failure Modes:
        Propagates connection errors raised by ``psycopg2.connect``.
    """
    settings = get_settings()
    conn = psycopg2.connect(**settings.db_config)
    try:
        yield conn
    finally:
        conn.close()


def get_db() -> Generator[PGConnection, None, None]:
    """Yield a database connection for FastAPI dependency injection.

    Returns:
        Generator[PGConnection, None, None]: Request-scoped database
        connection.

    Side Effects:
        Opens and closes a PostgreSQL connection around the dependency scope.

    Failure Modes:
        Propagates the same database connectivity errors as
        :func:`get_db_connection`.
    """
    with get_db_connection() as conn:
        yield conn
