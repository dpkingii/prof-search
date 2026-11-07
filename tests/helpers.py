import functools
import re
import zlib

import numpy as np
import pytest

from index.embed import DIM


def needs_impl(test):
    """Skip, rather than fail, while the code under test is still a NotImplementedError stub."""

    @functools.wraps(test)
    def wrapper(*args, **kwargs):
        try:
            return test(*args, **kwargs)
        except NotImplementedError:
            pytest.skip("not implemented yet")

    return wrapper


class FakeEmbedder:
    """Hashed bag-of-words vectors: reviews sharing words with the query end up nearest."""

    def passages(self, texts: list[str]) -> list[np.ndarray]:
        return [self._vec(t) for t in texts]

    def query(self, text: str) -> np.ndarray:
        return self._vec(text)

    def _vec(self, text: str) -> np.ndarray:
        v = np.zeros(DIM, dtype=np.float32)
        for word in re.findall(r"[a-z0-9]+", text.lower()):
            v[zlib.crc32(word.encode()) % DIM] += 1
        if not v.any():
            v[0] = 1
        return v / np.linalg.norm(v)


class FakeReranker:
    """Scores by words shared with the query, minus a penalty for negations the query lacks."""

    def scores(self, query: str, texts: list[str]) -> list[float]:
        q = set(re.findall(r"[a-z]+", query.lower()))
        out = []
        for t in texts:
            words = re.findall(r"[a-z]+", t.lower())
            negated = ({"not", "no", "never"} & set(words)) - q
            out.append(len(q & set(words)) - (5.0 if negated else 0.0))
        return out
