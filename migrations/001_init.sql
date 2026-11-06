CREATE TABLE professors (
    slug           text PRIMARY KEY,
    name           text NOT NULL,
    type           text NOT NULL,
    courses        text[] NOT NULL DEFAULT '{}',
    average_rating real,
    average_gpa    real,
    updated_at     timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE reviews (
    id             bigserial PRIMARY KEY,
    professor_slug text NOT NULL REFERENCES professors (slug),
    course         text,
    body           text NOT NULL,
    rating         smallint,
    expected_grade text,
    created_at     timestamptz,
    -- PlanetTerp reviews have no stable id, so dedupe on content.
    content_hash   text NOT NULL UNIQUE,
    tsv            tsvector GENERATED ALWAYS AS (
                       to_tsvector('english', coalesce(course, '') || ' ' || body)
                   ) STORED
);

CREATE INDEX reviews_tsv_idx ON reviews USING gin (tsv);
CREATE INDEX reviews_professor_idx ON reviews (professor_slug);
