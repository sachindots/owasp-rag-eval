-- vector(1024) matches bge-m3; change it together with EMBED_MODEL.
CREATE TABLE IF NOT EXISTS chunks (
    id text PRIMARY KEY,
    doc text NOT NULL,
    heading text NOT NULL,
    text text NOT NULL,
    embedding vector(1024) NOT NULL,
    tsv tsvector GENERATED ALWAYS AS (to_tsvector('english', heading || ' ' || text)) STORED
);

CREATE INDEX IF NOT EXISTS chunks_embedding_idx ON chunks USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS chunks_tsv_idx ON chunks USING gin (tsv);
