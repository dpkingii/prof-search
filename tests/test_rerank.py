from search.rerank import rerank
from tests.helpers import FakeReranker


def hit(id, body, score=0.5, chunk=None):
    h = {"id": id, "professor_slug": f"p{id}", "body": body, "score": score}
    if chunk is not None:
        h["chunk"] = chunk
    return h


def test_negated_review_drops_below_matching_one():
    hits = [hit(1, "Does not curve the exams."), hit(2, "Curves every exam, lenient grader.")]
    result = rerank(FakeReranker(), "lenient grader who curves exams", hits)
    assert [h["id"] for h in result] == [2, 1]


def test_scores_are_probabilities():
    hits = [hit(1, "Does not curve."), hit(2, "Curves exams.")]
    assert all(0 < h["score"] < 1 for h in rerank(FakeReranker(), "curves exams", hits))


def test_only_top_candidates_are_kept():
    hits = [hit(i, "exams") for i in range(10)]
    assert len(rerank(FakeReranker(), "exams", hits, top=3)) == 3


def test_scores_matched_chunk_when_present():
    hits = [hit(1, "long body about nothing", chunk="curves exams"), hit(2, "unrelated text")]
    assert rerank(FakeReranker(), "curves exams", hits)[0]["id"] == 1


def test_empty():
    assert rerank(FakeReranker(), "anything", []) == []


def test_long_text_is_truncated_before_scoring():
    seen = []

    class Spy(FakeReranker):
        def scores(self, query, texts):
            seen.extend(texts)
            return super().scores(query, texts)

    rerank(Spy(), "q", [hit(1, " ".join(["word"] * 500))])
    assert len(seen[0].split()) == 64
