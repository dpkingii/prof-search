"""Ranking metrics over professor slugs.

judgments maps slug -> graded relevance: 0 not relevant, 1 somewhat, 2 very.
Slugs missing from judgments count as 0. Queries with no relevant slug are skipped by
run_eval.py, so you can assume at least one grade >= 1.

Contract: tests/test_metrics.py
"""

import math


def recall_at_k(ranked: list[str], judgments: dict[str, int], k: int) -> float:
    """Fraction of relevant slugs (grade >= 1) that appear in ranked[:k]."""
    relevant = {slug for slug, grade in judgments.items() if grade >= 1}
    return len(relevant & set(ranked[:k])) / len(relevant)


def reciprocal_rank(ranked: list[str], judgments: dict[str, int]) -> float:
    """1 / rank of the first relevant slug (rank starts at 1), or 0.0 if none. MRR is its mean."""
    for rank, slug in enumerate(ranked, 1):
        if judgments.get(slug, 0) >= 1:
            return 1 / rank
    return 0.0


def _dcg(grades: list[int]) -> float:
    return sum((2**g - 1) / math.log2(rank + 1) for rank, g in enumerate(grades, 1))


def ndcg_at_k(ranked: list[str], judgments: dict[str, int], k: int) -> float:
    """DCG of ranked[:k] divided by the DCG of the ideal ordering of judgments.

    Use gain 2**grade - 1 and discount log2(rank + 1), rank starting at 1.
    """
    ideal = _dcg(sorted(judgments.values(), reverse=True)[:k])
    return _dcg([judgments.get(slug, 0) for slug in ranked[:k]]) / ideal
