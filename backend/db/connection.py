from contextlib import contextmanager
from typing import Generator, Iterator

import psycopg2
from psycopg2.extensions import connection as PGConnection

from backend.core.config import get_settings


@contextmanager
def get_db_connection() -> Iterator[PGConnection]:
    settings = get_settings()
    conn = psycopg2.connect(**settings.db_config)
    try:
        yield conn
    finally:
        conn.close()


def get_db() -> Generator[PGConnection, None, None]:
    with get_db_connection() as conn:
        yield conn
