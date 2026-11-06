from ingest.load import insert_reviews, upsert_professor
from search import keyword


def seed(conn):
    profs = [
        ("smith", "Ann Smith", [
            {"course": "CMSC216", "review": "Lenient grader and she posts all the lecture slides."},
            {"course": "CMSC216", "review": "Projects are long but grading is fair."},
        ]),
        ("jones", "Bob Jones", [
            {"course": "MATH140", "review": "Exams are brutal and he never curves."},
        ]),
    ]
    for slug, name, reviews in profs:
        upsert_professor(conn, {"slug": slug, "name": name, "type": "professor",
                                "courses": [], "average_rating": 4.0})
        insert_reviews(conn, slug, reviews)
    conn.commit()


def test_insert_reviews_is_idempotent(conn):
    upsert_professor(conn, {"slug": "smith", "name": "Ann Smith", "type": "professor",
                            "courses": ["CMSC216"], "average_rating": 4.0})
    reviews = [{"review": "Great.", "created": "2023-01-01T00:00:00Z"}]
    assert insert_reviews(conn, "smith", reviews) == 1
    assert insert_reviews(conn, "smith", reviews) == 0


def test_partial_term_match_ranks_best_review_first(conn):
    seed(conn)
    results = keyword.search(conn, "lenient grader who posts slides")
    assert results[0]["professor_slug"] == "smith"
    assert "Lenient" in results[0]["body"]


def test_course_code_is_searchable(conn):
    seed(conn)
    results = keyword.search(conn, "MATH140")
    assert [r["professor_slug"] for r in results] == ["jones"]


def test_stopword_only_query_returns_nothing(conn):
    seed(conn)
    assert keyword.search(conn, "the and of") == []

