from ingest.load import average_gpa, review_hash


def test_average_gpa_weights_by_students():
    sections = [{"A": 2, "B": 1}, {"C": 1}]
    assert average_gpa(sections) == round((4.0 * 2 + 3.0 + 2.0) / 4, 3)


def test_average_gpa_ignores_withdrawals():
    assert average_gpa([{"A": 1, "W": 5}]) == 4.0


def test_average_gpa_no_students():
    assert average_gpa([]) is None
    assert average_gpa([{"W": 3}]) is None


def test_review_hash_is_stable_and_distinguishes_reviews():
    r = {"review": "Great lecturer.", "created": "2023-01-01T00:00:00Z"}
    assert review_hash("smith", r) == review_hash("smith", dict(r))
    assert review_hash("smith", r) != review_hash("jones", r)
    assert review_hash("smith", r) != review_hash("smith", {**r, "review": "Bad lecturer."})
