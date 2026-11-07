from typing import Literal

import psycopg

from search import aggregate, fuse, keyword, rerank, vector

Mode = Literal["keyword", "vector", "hybrid", "rerank"]
MODES: tuple[Mode, ...] = ("keyword", "vector", "hybrid", "rerank")

# Reviews pulled per method before collapsing to professors.
CANDIDATES = 50


def review_hits(
    conn: psycopg.Connection, embedder, query: str, mode: Mode, reranker=None
) -> list[dict]:
    if mode == "keyword":
        return keyword.search(conn, query, CANDIDATES)
    if mode == "vector":
        return vector.search(conn, embedder.query(query), CANDIDATES)

    kw = keyword.search(conn, query, CANDIDATES)
    vec = vector.search(conn, embedder.query(query), CANDIDATES)
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
