"""Interactive relevance labeling.

For each query, pools the top professors from every search mode and asks for a 0/1/2 grade
on each one not yet judged. Judgments are written back to queries.jsonl after every answer.
With --gen-eds, pools gen-ed courses for gen_ed_queries.jsonl instead.
"""

import argparse
import json
import textwrap
from pathlib import Path

from pgvector.psycopg import register_vector

import db
from index.embed import Embedder
from search import pipeline
from search.rerank import Reranker

QUERIES = Path(__file__).parent / "queries.jsonl"
GEN_ED_QUERIES = Path(__file__).parent / "gen_ed_queries.jsonl"


def load(path: Path = QUERIES) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def save(queries: list[dict], path: Path = QUERIES) -> None:
    path.write_text("".join(json.dumps(q, ensure_ascii=False) + "\n" for q in queries))


def pool_candidates(conn, embedder, reranker, query: str, depth: int) -> dict[str, dict]:
    pooled: dict[str, dict] = {}
    for mode in pipeline.MODES:
        for prof in pipeline.search(conn, embedder, query, mode, depth, reranker):
            pooled.setdefault(prof["slug"], prof)
    return pooled


def pool_gen_eds(conn, embedder, reranker, q: dict, depth: int) -> dict[str, dict]:
    pooled: dict[str, dict] = {}
    for mode in pipeline.MODES:
        for course in pipeline.search_gen_eds(
            conn, embedder, q["query"], mode, depth, reranker, q.get("gen_ed")
        ):
            pooled.setdefault(course["course_id"], course)
    return pooled


def heading(result: dict) -> str:
    if "course_id" in result:
        return f"{result['course_id']} {result['name']}  gen-eds={','.join(result['gen_eds'])}"
    return f"{result['name']}  rating={result['average_rating']}"


def ask(prompt: str) -> str:
    while True:
        answer = input(prompt).strip().lower()
        if answer in {"0", "1", "2", "s", "q"}:
            return answer


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--depth", type=int, default=20, help="results pooled per mode")
    parser.add_argument("--only", help="label a single query id")
    parser.add_argument("--gen-eds", action="store_true", help="label gen-ed course queries")
    args = parser.parse_args()

    path = GEN_ED_QUERIES if args.gen_eds else QUERIES
    queries = load(path)
    embedder = Embedder()
    reranker = Reranker()
    with db.connect() as conn:
        register_vector(conn)
        for q in queries:
            if args.only and q["id"] != args.only:
                continue
            judgments = q.setdefault("judgments", {})
            if args.gen_eds:
                pooled = pool_gen_eds(conn, embedder, reranker, q, args.depth)
            else:
                pooled = pool_candidates(conn, embedder, reranker, q["query"], args.depth)
            todo = [p for s, p in pooled.items() if s not in judgments]
            for i, prof in enumerate(todo, 1):
                scope = f"  [{q['gen_ed']}]" if q.get("gen_ed") else ""
                print(f"\n[{q['id']}] {q['query']}{scope}  ({i}/{len(todo)})")
                print(f"  {heading(prof)}")
                for snippet in prof["snippets"]:
                    print(textwrap.indent(textwrap.fill(snippet[:400], 96), "    | "))
                answer = ask("  relevance [0/1/2, s=skip, q=quit]: ")
                if answer == "q":
                    return
                if answer != "s":
                    judgments[prof.get("course_id") or prof["slug"]] = int(answer)
                    save(queries, path)


if __name__ == "__main__":
    main()
