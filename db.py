import os

import psycopg
from psycopg.rows import dict_row

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://review:review@localhost:5433/review"
)


def connect(url: str = DATABASE_URL) -> psycopg.Connection:
    return psycopg.connect(url, row_factory=dict_row)
