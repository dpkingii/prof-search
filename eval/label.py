"""Interactive relevance labeling.

For each query, pools the top professors from every search mode and asks for a 0/1/2 grade
on each one not yet judged. Judgments are written back to queries.jsonl after every answer.
"""

import argparse
import json
import textwrap
from pathlib import Path

from pgvector.psycopg import register_vector

import db
from index.embed import Embedder
from search import pipeline

QUERIES = Path(__file__).parent / "queries.jsonl"


def load(path: Path = QUERIES) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def save(queries: list[dict], path: Path = QUERIES) -> None:
    path.write_text("".join(json.dumps(q, ensure_ascii=False) + "\n" for q in queries))


def pool_candidates(conn, embedder, query: str, depth: int) -> dict[str, dict]:
    pooled: dict[str, dict] = {}
    for mode in pipeline.MODES:
        for prof in pipeline.search(conn, embedder, query, mode, depth):
            pooled.setdefault(prof["slug"], prof)
    return pooled


def ask(prompt: str) -> str:
    while True:
        answer = input(prompt).strip().lower()
        if answer in {"0", "1", "2", "s", "q"}:
            return answer


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--depth", type=int, default=20, help="professors pooled per mode")
    parser.add_argument("--only", help="label a single query id")
    args = parser.parse_args()

    queries = load()
    embedder = Embedder()
    with db.connect() as conn:
        register_vector(conn)
        for q in queries:
            if args.only and q["id"] != args.only:
                continue
            judgments = q.setdefault("judgments", {})
            todo = [p for s, p in pool_candidates(conn, embedder, q["query"], args.depth).items()
                    if s not in judgments]
            for i, prof in enumerate(todo, 1):
                print(f"\n[{q['id']}] {q['query']}  ({i}/{len(todo)})")
                print(f"  {prof['name']}  rating={prof['average_rating']}")
                for snippet in prof["snippets"]:
                    print(textwrap.indent(textwrap.fill(snippet[:400], 96), "    | "))
                answer = ask("  relevance [0/1/2, s=skip, q=quit]: ")
                if answer == "q":
                    return
                if answer != "s":
                    judgments[prof["slug"]] = int(answer)
                    save(queries)


if __name__ == "__main__":
    main()
