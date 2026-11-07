import math

from fastembed.rerank.cross_encoder import TextCrossEncoder

MODEL = "Xenova/ms-marco-MiniLM-L-6-v2"
# Fused candidates rescored per query. The cross-encoder runs once per (query, review) pair,
# so this is the knob that trades latency for recall.
TOP = 50
# MS MARCO passages, which this model was trained on, average ~56 words. Feeding it whole
# 200-word chunks was 3x slower and scored lower on the eval.
MAX_WORDS = 64


class Reranker:
    def __init__(self, model: str = MODEL):
        self.model = TextCrossEncoder(model)

    def scores(self, query: str, texts: list[str]) -> list[float]:
        return list(self.model.rerank(query, texts))


def rerank(reranker, query: str, hits: list[dict], top: int = TOP) -> list[dict]:
    """Rescore the first `top` hits by reading query and review text together.

    Cross-encoder logits are unbounded and often negative, which would make
    aggregate.professors' sum of top hits penalize professors for extra weak matches,
    so they are squashed to (0, 1) first.
    """
    candidates = hits[:top]
    if not candidates:
        return []
    texts = [" ".join((h.get("chunk") or h["body"]).split()[:MAX_WORDS]) for h in candidates]
    logits = reranker.scores(query, texts)
    rescored = [{**h, "score": 1 / (1 + math.exp(-s))} for h, s in zip(candidates, logits)]
    return sorted(rescored, key=lambda h: (-h["score"], h["id"]))
