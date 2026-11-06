import pytest

from search.fuse import reciprocal_rank_fusion
from tests.helpers import needs_impl


@needs_impl
def test_score_formula():
    assert reciprocal_rank_fusion([[7]], k=60) == [(7, pytest.approx(1 / 61))]


@needs_impl
def test_single_list_keeps_order():
    assert [i for i, _ in reciprocal_rank_fusion([[3, 1, 2]])] == [3, 1, 2]


@needs_impl
def test_item_in_both_lists_beats_item_in_one():
    fused = reciprocal_rank_fusion([[1, 2], [2, 3]])
    assert fused[0][0] == 2
    assert fused[0][1] == pytest.approx(1 / 62 + 1 / 61)


@needs_impl
def test_ties_broken_by_smaller_id():
    assert [i for i, _ in reciprocal_rank_fusion([[2], [1]])] == [1, 2]


@needs_impl
def test_empty():
    assert reciprocal_rank_fusion([]) == []
    assert reciprocal_rank_fusion([[], []]) == []
