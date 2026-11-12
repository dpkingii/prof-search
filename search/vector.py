import numpy as np
import psycopg

# Fetch extra chunks so several chunks of one review still leave k distinct reviews.
CANDIDATE_MULTIPLIER = 4

SEARCH_SQL = """
WITH nearest AS (
    SELECT review_id, body, embedding <=> %(v)s AS distance
    FROM chunks
    {course_filter}
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

COURSE_FILTER = "WHERE review_id IN (SELECT id FROM reviews WHERE course = ANY(%(courses)s))"


def search(
    conn: psycopg.Connection,
    query_vector: np.ndarray,
    k: int = 10,
    courses: list[str] | None = None,
) -> list[dict]:
    """courses, when given, restricts results to reviews of those courses."""
    candidates = k * CANDIDATE_MULTIPLIER
    # HNSW returns at most ef_search rows (default 40), which would silently cap LIMIT.
    # A course filter runs on rows the index already returned, so a plain scan would come back
    # short. Iterative scan keeps walking the graph until LIMIT rows pass the filter. Set on
    # every call because the setting lasts for the transaction, which eval scripts share.
    conn.execute(
        "SELECT set_config('hnsw.ef_search', %s, true),"
        " set_config('hnsw.iterative_scan', %s, true)",
        (str(max(40, candidates)), "off" if courses is None else "strict_order"),
    )
    sql = SEARCH_SQL.format(course_filter="" if courses is None else COURSE_FILTER)
    return conn.execute(
        sql, {"v": query_vector, "candidates": candidates, "k": k, "courses": courses}
    ).fetchall()
