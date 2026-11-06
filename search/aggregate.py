# A professor's score is a rank-discounted sum of their best TOP_N hits: s1 + s2/2 + s3/3.
# Several matching reviews are stronger evidence than one, but capping at TOP_N keeps
# professors with hundreds of reviews from winning on volume. Being a weighted sum, it
# works the same for keyword, cosine, and RRF scores without normalizing them.
TOP_N = 3


def professors(hits: list[dict], limit: int = 10, snippets: int = 3) -> list[dict]:
    """Collapse review-level hits into a ranked list of professors.

    hits are best first. Each has id, professor_slug, professor_name, average_rating, score,
    and body. Vector and hybrid hits may also have chunk, the part of the review that matched.

    Returns at most `limit` dicts, best first:
        {"slug", "name", "average_rating", "score", "snippets": [str, ...]}
    with up to `snippets` snippets per professor, each the hit's chunk if it has one, else body.

    Contract: tests/test_aggregate.py
    """
    groups: dict[str, dict] = {}
    for hit in hits:
        group = groups.setdefault(hit["professor_slug"], {
            "slug": hit["professor_slug"],
            "name": hit["professor_name"],
            "average_rating": hit["average_rating"],
            "hits": [],
        })
        group["hits"].append(hit)

    results = []
    for group in groups.values():
        ranked = sorted(group.pop("hits"), key=lambda h: -h["score"])
        group["score"] = sum(h["score"] / i for i, h in enumerate(ranked[:TOP_N], 1))
        group["snippets"] = [h.get("chunk") or h["body"] for h in ranked[:snippets]]
        results.append(group)
    results.sort(key=lambda g: (-g["score"], g["slug"]))
    return results[:limit]
