from typing import Literal

import psycopg

from search import aggregate, fuse, keyword, vector

Mode = Literal["keyword", "vector", "hybrid"]
MODES: tuple[Mode, ...] = ("keyword", "vector", "hybrid")

# Reviews pulled per method before collapsing to professors.
CANDIDATES = 50


def review_hits(conn: psycopg.Connection, embedder, query: str, mode: Mode) -> list[dict]:
    if mode == "keyword":
        return keyword.search(conn, query, CANDIDATES)
    if mode == "vector":
        return vector.search(conn, embedder.query(query), CANDIDATES)

    kw = keyword.search(conn, query, CANDIDATES)
    vec = vector.search(conn, embedder.query(query), CANDIDATES)
    # Vector hits carry the matched chunk, so let them win when a review is in both lists.
    by_id = {h["id"]: h for h in kw} | {h["id"]: h for h in vec}
    fused = fuse.reciprocal_rank_fusion([[h["id"] for h in kw], [h["id"] for h in vec]])
    return [{**by_id[i], "score": s} for i, s in fused]


def search(
    conn: psycopg.Connection, embedder, query: str, mode: Mode = "hybrid", k: int = 10
) -> list[dict]:
    return aggregate.professors(review_hits(conn, embedder, query, mode), limit=k)
