import argparse
import time
from collections.abc import Callable

import numpy as np
import psycopg
from fastembed import TextEmbedding
from pgvector.psycopg import register_vector

import db
from index.chunk import chunk

MODEL = "BAAI/bge-small-en-v1.5"
DIM = 384
# bge models are trained with this instruction on queries only, not on passages.
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


class Embedder:
    def __init__(self, model: str = MODEL):
        self.model = TextEmbedding(model)

    def passages(self, texts: list[str]) -> list[np.ndarray]:
        return list(self.model.passage_embed(texts))

    def query(self, text: str) -> np.ndarray:
        return next(iter(self.model.query_embed(QUERY_PREFIX + text)))


def index_reviews(
    conn: psycopg.Connection,
    embedder,
    batch_size: int = 256,
    chunker: Callable[[str], list[str]] = chunk,
    progress: Callable[[int, int], None] | None = None,
) -> int:
    """Chunk and embed every review that has no chunks yet. Returns the number of chunks written."""
    last_id = 0
    reviews_done = chunks_written = 0
    while True:
        rows = conn.execute(
            """
            SELECT r.id, r.body FROM reviews r
            WHERE r.id > %s AND NOT EXISTS (SELECT 1 FROM chunks c WHERE c.review_id = r.id)
            ORDER BY r.id LIMIT %s
            """,
            (last_id, batch_size),
        ).fetchall()
        if not rows:
            return chunks_written
        last_id = rows[-1]["id"]

        pending = [(r["id"], i, body) for r in rows for i, body in enumerate(chunker(r["body"]))]
        vectors = embedder.passages([body for _, _, body in pending])
        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO chunks (review_id, ordinal, body, embedding) VALUES (%s, %s, %s, %s)",
                [(*p, v) for p, v in zip(pending, vectors)],
            )
        conn.commit()

        reviews_done += len(rows)
        chunks_written += len(pending)
        if progress:
            progress(reviews_done, chunks_written)


def main() -> None:
    parser = argparse.ArgumentParser(description="Chunk and embed reviews into pgvector.")
    parser.add_argument("--rebuild", action="store_true", help="drop all chunks first (e.g. after changing chunk.py)")
    parser.add_argument("--batch-size", type=int, default=256)
    args = parser.parse_args()

    with db.connect() as conn:
        register_vector(conn)
        if args.rebuild:
            conn.execute("TRUNCATE chunks")
            conn.commit()
        start = time.monotonic()
        written = index_reviews(
            conn,
            Embedder(),
            batch_size=args.batch_size,
            progress=lambda r, c: print(f"\rreviews: {r}  chunks: {c}", end="", flush=True),
        )
    print(f"\nwrote {written} chunks in {time.monotonic() - start:.0f}s")


if __name__ == "__main__":
    main()
