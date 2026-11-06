import math

import pytest

from eval.metrics import ndcg_at_k, recall_at_k, reciprocal_rank
from tests.helpers import needs_impl

JUDGMENTS = {"a": 2, "b": 0, "c": 1, "d": 1}


@needs_impl
def test_recall_at_k():
    assert recall_at_k(["a", "b", "c"], JUDGMENTS, k=3) == pytest.approx(2 / 3)
    assert recall_at_k(["a", "b", "c"], JUDGMENTS, k=1) == pytest.approx(1 / 3)
    assert recall_at_k(["x", "y"], JUDGMENTS, k=2) == 0.0


@needs_impl
def test_reciprocal_rank():
    assert reciprocal_rank(["b", "x", "c"], JUDGMENTS) == pytest.approx(1 / 3)
    assert reciprocal_rank(["a"], JUDGMENTS) == 1.0
    assert reciprocal_rank(["b", "x"], JUDGMENTS) == 0.0


@needs_impl
def test_ndcg_at_k():
    dcg = 0 / math.log2(2) + 3 / math.log2(3) + 1 / math.log2(4)
    ideal = 3 / math.log2(2) + 1 / math.log2(3) + 1 / math.log2(4)
    assert ndcg_at_k(["b", "a", "c"], JUDGMENTS, k=3) == pytest.approx(dcg / ideal)


@needs_impl
def test_ndcg_perfect_and_unjudged():
    assert ndcg_at_k(["a", "c", "d"], JUDGMENTS, k=3) == pytest.approx(1.0)
    assert ndcg_at_k(["x", "y", "z"], JUDGMENTS, k=3) == 0.0
