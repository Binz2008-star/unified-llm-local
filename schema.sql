-- schema.sql - Run once in Neon SQL Editor
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS chunks (
    id SERIAL PRIMARY KEY,
    project_id TEXT NOT NULL,
    file_path TEXT NOT NULL,
    chunk_index INT NOT NULL,
    content TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    language TEXT,
    start_line INT,
    end_line INT,
    embedding vector(768),
    indexed_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(project_id, file_path, chunk_index)
);

CREATE INDEX IF NOT EXISTS idx_chunks_project_file ON chunks(project_id, file_path);
CREATE INDEX IF NOT EXISTS idx_chunks_hash ON chunks(content_hash);
-- Create after you have >1000 rows for best performance:
-- CREATE INDEX idx_chunks_embedding ON chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists=100);

CREATE TABLE IF NOT EXISTS second_brain (
    id SERIAL PRIMARY KEY,
    type TEXT NOT NULL CHECK (type IN ('decision','error_fix','pattern','session_log','github_issue')),
    project_id TEXT,
    title TEXT,
    content TEXT NOT NULL,
    source_file TEXT,
    embedding vector(768),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- For hybrid search
CREATE INDEX IF NOT EXISTS idx_chunks_content_trgm ON chunks USING gin (content gin_trgm_ops);