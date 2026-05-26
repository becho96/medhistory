-- Migration: Semantic search support — pgvector embeddings on document summaries
-- Date: 2026-05-26
--
-- Adds a 768-dim vector column (multilingual-e5-base) to documents and an HNSW
-- index for cosine similarity. The column is nullable; new documents are
-- populated by the embeddings sidecar at processing time, existing rows are
-- backfilled by scripts/backfill_embeddings.py.

BEGIN;

CREATE EXTENSION IF NOT EXISTS vector;

ALTER TABLE documents
    ADD COLUMN IF NOT EXISTS embedding vector(768);

-- HNSW: no training step required (unlike ivfflat), fast on small/medium sets,
-- handles incremental inserts gracefully.
CREATE INDEX IF NOT EXISTS idx_documents_embedding_hnsw
    ON documents
    USING hnsw (embedding vector_cosine_ops);

COMMIT;
