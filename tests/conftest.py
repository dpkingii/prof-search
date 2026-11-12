import os

# Point everything (including api.main's pool) at the test database before app modules import.
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql://review:review@localhost:5433/review_test"
)
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

import psycopg
import pytest
from pgvector.psycopg import register_vector

import db
from migrate import migrate


@pytest.fixture
def conn():
    try:
        c = db.connect(TEST_DATABASE_URL)
    except psycopg.OperationalError as e:
        pytest.skip(f"test database unavailable: {e}")
    migrate(c)
    register_vector(c)
    c.execute("TRUNCATE chunks, reviews, professors, gen_ed_courses RESTART IDENTITY")
    c.commit()
    yield c
    c.close()
