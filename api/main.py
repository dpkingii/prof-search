from contextlib import asynccontextmanager
from functools import cache
from pathlib import Path
from typing import Annotated

import psycopg
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.staticfiles import StaticFiles
from pgvector.psycopg import register_vector
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

import db
from index.embed import Embedder
from search import pipeline
from search.rerank import Reranker


@asynccontextmanager
async def lifespan(app: FastAPI):
    with ConnectionPool(
        db.DATABASE_URL, kwargs={"row_factory": dict_row}, configure=register_vector
    ) as pool:
        app.state.pool = pool
        yield


app = FastAPI(title="prof-search", lifespan=lifespan)


def get_conn(request: Request):
    with request.app.state.pool.connection() as conn:
        yield conn


Conn = Annotated[psycopg.Connection, Depends(get_conn)]


@cache
def get_embedder() -> Embedder:
    return Embedder()


@cache
def get_reranker() -> Reranker:
    return Reranker()


@app.get("/healthz")
def healthz(conn: Conn):
    conn.execute("SELECT 1")
    return {"ok": True}


@app.get("/search")
def search(
    conn: Conn,
    embedder: Annotated[Embedder, Depends(get_embedder)],
    reranker: Annotated[Reranker, Depends(get_reranker)],
    q: str = Query(min_length=1, max_length=200),
    k: int = Query(10, ge=1, le=50),
    mode: pipeline.Mode = "rerank",
):
    return {"query": q, "mode": mode, "results": pipeline.search(conn, embedder, q, mode, k, reranker)}


@app.get("/professors/{slug}")
def professor(slug: str, conn: Conn):
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


# Mounted last so the API routes above take precedence over static files.
app.mount("/", StaticFiles(directory=Path(__file__).parent.parent / "web", html=True), name="web")
