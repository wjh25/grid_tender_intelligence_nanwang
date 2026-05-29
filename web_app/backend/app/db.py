from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from app.config import settings


pool = ConnectionPool(
    conninfo=settings.database_url,
    min_size=1,
    max_size=8,
    kwargs={"row_factory": dict_row},
    open=False,
)


def open_pool() -> None:
    pool.open(wait=True)


def close_pool() -> None:
    pool.close()


@contextmanager
def cursor() -> Iterator[Any]:
    with pool.connection() as conn:
        with conn.cursor() as cur:
            yield cur

