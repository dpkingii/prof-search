import numpy as np
import psycopg

# Fetch extra chunks so several chunks of one review still leave k distinct reviews.
CANDIDATE_MULTIPLIER = 4

SEARCH_SQL = """
WITH nearest AS (
    SELECT review_id, body, embedding <=> %(v)s AS distance
    FROM chunks
    ORDER BY embedding <=> %(v)s
    LIMIT %(candidates)s
),
best AS (
    SELECT DISTINCT ON (review_id) review_id, body AS chunk, distance
    FROM nearest
    ORDER BY review_id, distance
)
SELECT
    r.id,
    r.professor_slug,
    p.name AS professor_name,
    r.course,
    r.body,
    b.chunk,
    r.rating,
    p.average_rating,
    1 - b.distance AS score
FROM best b
JOIN reviews r ON r.id = b.review_id
JOIN professors p ON p.slug = r.professor_slug
ORDER BY b.distance, r.id
LIMIT %(k)s
"""


def search(conn: psycopg.Connection, query_vector: np.ndarray, k: int = 10) -> list[dict]:
    candidates = k * CANDIDATE_MULTIPLIER
    # HNSW returns at most ef_search rows (default 40), which would silently cap LIMIT.
    conn.execute("SELECT set_config('hnsw.ef_search', %s, true)", (str(max(40, candidates)),))
    return conn.execute(
        SEARCH_SQL, {"v": query_vector, "candidates": candidates, "k": k}
    ).fetchall()
