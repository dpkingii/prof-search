import psycopg

# OR the query's lexemes together instead of websearch_to_tsquery's implicit AND,
# so a long natural-language query still matches reviews that hit only some terms.
# Lexemes are already stemmed, so the 'simple' config keeps them from being re-stemmed.
SEARCH_SQL = """
WITH q AS (
    SELECT to_tsquery('simple', string_agg(quote_literal(lexeme), ' | ')) AS query
    FROM unnest(to_tsvector('english', %(q)s))
)
SELECT
    r.id,
    r.professor_slug,
    p.name AS professor_name,
    r.course,
    r.body,
    r.rating,
    p.average_rating,
    ts_rank(r.tsv, q.query, 1) AS score
FROM reviews r
JOIN professors p ON p.slug = r.professor_slug
CROSS JOIN q
WHERE r.tsv @@ q.query {course_filter}
ORDER BY score DESC, r.id
LIMIT %(k)s
"""

COURSE_FILTER = "AND r.course = ANY(%(courses)s)"


def search(
    conn: psycopg.Connection, query: str, k: int = 10, courses: list[str] | None = None
) -> list[dict]:
    """courses, when given, restricts results to reviews of those courses."""
    sql = SEARCH_SQL.format(course_filter="" if courses is None else COURSE_FILTER)
    return conn.execute(sql, {"q": query, "k": k, "courses": courses}).fetchall()
