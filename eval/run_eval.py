"""Compare search modes on the labeled queries and print markdown tables."""

import argparse
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
from pgvector.psycopg import register_vector

import db
from eval import metrics
from eval.label import load
from index.embed import Embedder
from search import pipeline
from search.rerank import Reranker


def evaluate(conn, embedder, reranker, queries: list[dict], modes, k: int) -> dict[str, dict]:
    report = {}
    for mode in modes:
        pipeline.search(conn, embedder, "warm up", mode, k, reranker)
        rows = []
        for q in queries:
            start = time.perf_counter()
            ranked = [p["slug"] for p in pipeline.search(conn, embedder, q["query"], mode, k, reranker)]
            ms = (time.perf_counter() - start) * 1000
            j = q["judgments"]
            rows.append({
                "type": q.get("type", "other"),
                "recall": metrics.recall_at_k(ranked, j, k),
                "rr": metrics.reciprocal_rank(ranked, j),
                "ndcg": metrics.ndcg_at_k(ranked, j, k),
                "ms": ms,
            })
        by_type = defaultdict(list)
        for r in rows:
            by_type[r["type"]].append(r["ndcg"])
        latencies = [r["ms"] for r in rows]
        report[mode] = {
            "recall": np.mean([r["recall"] for r in rows]),
            "mrr": np.mean([r["rr"] for r in rows]),
            "ndcg": np.mean([r["ndcg"] for r in rows]),
            "p50": np.percentile(latencies, 50),
            "p95": np.percentile(latencies, 95),
            "by_type": {t: (len(v), np.mean(v)) for t, v in by_type.items()},
        }
    return report


def render(report: dict[str, dict], k: int, n: int) -> str:
    lines = [
        f"{n} labeled queries, k={k}. Latency is in-process and includes query embedding.",
        "",
        f"| Method | Recall@{k} | MRR | nDCG@{k} | p50 ms | p95 ms |",
        "|---|---|---|---|---|---|",
    ]
    for mode, r in report.items():
        lines.append(
            f"| {mode} | {r['recall']:.3f} | {r['mrr']:.3f} | {r['ndcg']:.3f}"
            f" | {r['p50']:.1f} | {r['p95']:.1f} |"
        )
    modes = list(report)
    types = sorted({t for r in report.values() for t in r["by_type"]})
    lines += ["", f"nDCG@{k} by query type:", "",
              "| Type | n | " + " | ".join(modes) + " |",
              "|---|---|" + "---|" * len(modes)]
    for t in types:
        n_t = report[modes[0]]["by_type"][t][0]
        cells = " | ".join(f"{report[m]['by_type'][t][1]:.3f}" for m in modes)
        lines.append(f"| {t} | {n_t} | {cells} |")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--k", type=int, default=10)
    parser.add_argument("--modes", nargs="+", default=list(pipeline.MODES), choices=pipeline.MODES)
    parser.add_argument("--out", type=Path, help="also write the tables to this file")
    args = parser.parse_args()

    queries = [q for q in load() if any(g >= 1 for g in q.get("judgments", {}).values())]
    if not queries:
        raise SystemExit("no labeled queries yet; run python -m eval.label first")

    with db.connect() as conn:
        register_vector(conn)
        table = render(evaluate(conn, Embedder(), Reranker(), queries, args.modes, args.k), args.k, len(queries))
    print(table)
    if args.out:
        args.out.write_text(table + "\n")


if __name__ == "__main__":
    main()
