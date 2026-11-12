import pytest

from search.aggregate import courses, professors
from tests.helpers import needs_impl


def hit(id, slug, score, body, chunk=None):
    h = {"id": id, "professor_slug": slug, "professor_name": slug.title(),
         "average_rating": 4.0, "score": score, "body": body}
    if chunk is not None:
        h["chunk"] = chunk
    return h


HITS = [
    hit(1, "smith", 0.9, "smith one"),
    hit(2, "jones", 0.8, "jones one"),
    hit(3, "smith", 0.7, "smith two"),
    hit(4, "lee", 0.6, "lee one"),
    hit(5, "smith", 0.5, "smith three"),
    hit(6, "smith", 0.4, "smith four"),
]


@needs_impl
def test_one_entry_per_professor_best_first():
    result = professors(HITS)
    slugs = [p["slug"] for p in result]
    assert sorted(slugs) == ["jones", "lee", "smith"]
    scores = [p["score"] for p in result]
    assert scores == sorted(scores, reverse=True)


@needs_impl
def test_result_shape():
    p = next(p for p in professors(HITS) if p["slug"] == "jones")
    assert p["name"] == "Jones"
    assert p["average_rating"] == 4.0
    assert p["snippets"] == ["jones one"]


@needs_impl
def test_limit_and_snippet_cap():
    assert len(professors(HITS, limit=2)) == 2
    smith = next(p for p in professors(HITS, snippets=3) if p["slug"] == "smith")
    assert len(smith["snippets"]) == 3
    assert set(smith["snippets"]) <= {"smith one", "smith two", "smith three", "smith four"}


@needs_impl
def test_prefers_matched_chunk_over_full_body():
    result = professors([hit(1, "smith", 0.9, "long full review", chunk="matched part")])
    assert result[0]["snippets"] == ["matched part"]


@needs_impl
def test_empty():
    assert professors([]) == []


def course_hit(id, course, score, body):
    return {**hit(id, "smith", score, body), "course": course}


COURSE_HITS = [
    course_hit(1, None, 0.95, "no course"),
    course_hit(2, "ENGL101", 0.9, "engl one"),
    course_hit(3, "HIST200", 0.8, "hist one"),
    course_hit(4, "ENGL101", 0.7, "engl two"),
]


def test_courses_groups_by_course_and_drops_hits_without_one():
    result = courses(COURSE_HITS)
    assert [c["course_id"] for c in result] == ["ENGL101", "HIST200"]
    assert result[0]["score"] == pytest.approx(0.9 + 0.7 / 2)
    assert result[0]["snippets"] == ["engl one", "engl two"]


def test_courses_limit_and_empty():
    assert len(courses(COURSE_HITS, limit=1)) == 1
    assert courses([]) == []
