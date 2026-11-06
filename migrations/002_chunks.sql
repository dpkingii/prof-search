CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE chunks (
    id        bigserial PRIMARY KEY,
    review_id bigint NOT NULL REFERENCES reviews (id) ON DELETE CASCADE,
    ordinal   int NOT NULL,
    body      text NOT NULL,
    embedding vector(384) NOT NULL,
    UNIQUE (review_id, ordinal)
);

CREATE INDEX chunks_embedding_idx ON chunks USING hnsw (embedding vector_cosine_ops);
