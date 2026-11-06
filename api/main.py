from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

import db
from search import keyword

pool = ConnectionPool(db.DATABASE_URL, kwargs={"row_factory": dict_row}, open=False)


@asynccontextmanager
async def lifespan(app: FastAPI):
    pool.open()
    yield
    pool.close()


app = FastAPI(title="review-search", lifespan=lifespan)


@app.get("/healthz")
def healthz():
    with pool.connection() as conn:
        conn.execute("SELECT 1")
    return {"ok": True}


@app.get("/search")
def search(q: str = Query(min_length=1, max_length=200), k: int = Query(10, ge=1, le=50)):
    with pool.connection() as conn:
        results = keyword.search(conn, q, k)
    return {"query": q, "results": results}


@app.get("/professors/{slug}")
def professor(slug: str):
    with pool.connection() as conn:
        row = conn.execute(
            """
            SELECT p.slug, p.name, p.type, p.courses, p.average_rating, p.average_gpa,
                   count(r.id) AS review_count
            FROM professors p LEFT JOIN reviews r ON r.professor_slug = p.slug
            WHERE p.slug = %s
            GROUP BY p.slug
            """,
            (slug,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="professor not found")
    return row
