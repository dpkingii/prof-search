import itertools

from index.chunk import chunk
from tests.helpers import needs_impl


@needs_impl
def test_empty_text():
    assert chunk("") == []
    assert chunk("   \n ") == []


@needs_impl
def test_short_review_is_one_chunk():
    assert chunk("Great professor, fair exams.") == ["Great professor, fair exams."]


@needs_impl
def test_long_review_is_split_within_limit_and_covers_every_word():
    words = [f"w{i}" for i in range(450)]
    chunks = [c.split() for c in chunk(" ".join(words), max_words=200, overlap=30)]

    assert len(chunks) > 1
    assert all(len(c) <= 200 for c in chunks)
    assert chunks[0][0] == "w0" and chunks[-1][-1] == "w449"
    covered = {w for c in chunks for w in c}
    assert covered == set(words)


@needs_impl
def test_consecutive_chunks_overlap_and_stay_in_order():
    words = [f"w{i}" for i in range(450)]
    chunks = [c.split() for c in chunk(" ".join(words), max_words=200, overlap=30)]

    for a, b in itertools.pairwise(chunks):
        assert set(a) & set(b)
        assert int(b[0][1:]) > int(a[0][1:])
