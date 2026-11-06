def reciprocal_rank_fusion(rankings: list[list[int]], k: int = 60) -> list[tuple[int, float]]:
    """Merge several best-first rankings of review ids into one.

    Each id scores sum(1 / (k + rank)) over the lists it appears in, with rank starting at 1.
    Only ranks are used, so keyword and vector scores never need to be on the same scale.
    k=60 is the value from the original RRF paper (Cormack et al., 2009).

    Returns (id, score) pairs, highest score first, ties broken by smaller id.
    Contract: tests/test_fuse.py
    """
    scores: dict[int, float] = {}
    for ranking in rankings:
        for rank, review_id in enumerate(ranking, 1):
            scores[review_id] = scores.get(review_id, 0.0) + 1 / (k + rank)
    return sorted(scores.items(), key=lambda item: (-item[1], item[0]))
