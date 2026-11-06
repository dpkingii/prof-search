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
WHERE r.tsv @@ q.query
ORDER BY score DESC, r.id
LIMIT %(k)s
"""


def search(conn: psycopg.Connection, query: str, k: int = 10) -> list[dict]:
    return conn.execute(SEARCH_SQL, {"q": query, "k": k}).fetchall()
