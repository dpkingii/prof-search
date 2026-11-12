from typing import Literal

import psycopg

from search import aggregate, fuse, keyword, rerank, vector

Mode = Literal["keyword", "vector", "hybrid", "rerank"]
MODES: tuple[Mode, ...] = ("keyword", "vector", "hybrid", "rerank")

# Reviews pulled per method before collapsing to professors.
CANDIDATES = 50


def review_hits(
    conn: psycopg.Connection,
    embedder,
    query: str,
    mode: Mode,
    reranker=None,
    courses: list[str] | None = None,
) -> list[dict]:
    if mode == "keyword":
        return keyword.search(conn, query, CANDIDATES, courses)
    if mode == "vector":
        return vector.search(conn, embedder.query(query), CANDIDATES, courses)

    kw = keyword.search(conn, query, CANDIDATES, courses)
    vec = vector.search(conn, embedder.query(query), CANDIDATES, courses)
    # Vector hits carry the matched chunk, so let them win when a review is in both lists.
    by_id = {h["id"]: h for h in kw} | {h["id"]: h for h in vec}
    fused = fuse.reciprocal_rank_fusion([[h["id"] for h in kw], [h["id"] for h in vec]])
    hits = [{**by_id[i], "score": s} for i, s in fused]
    if mode == "rerank":
        return rerank.rerank(reranker, query, hits)
    return hits


def search(
    conn: psycopg.Connection,
    embedder,
    query: str,
    mode: Mode = "rerank",
    k: int = 10,
    reranker=None,
) -> list[dict]:
    return aggregate.professors(review_hits(conn, embedder, query, mode, reranker), limit=k)


def search_gen_eds(
    conn: psycopg.Connection,
    embedder,
    query: str,
    mode: Mode = "hybrid",
    k: int = 10,
    reranker=None,
    gen_ed: str | None = None,
) -> list[dict]:
    """Rank gen-ed courses by their reviews, optionally only those with one gen-ed code.

    Returns {"course_id", "name", "gen_eds", "score", "snippets"} dicts, best first.
    """
    rows = conn.execute(
        "SELECT course_id, name, gen_eds FROM gen_ed_courses"
        " WHERE %(gen_ed)s::text IS NULL OR %(gen_ed)s = ANY(gen_eds)",
        {"gen_ed": gen_ed},
    ).fetchall()
    info = {r["course_id"]: r for r in rows}
    hits = review_hits(conn, embedder, query, mode, reranker, courses=list(info))
    return [{**info[c["course_id"]], **c} for c in aggregate.courses(hits, limit=k)]
