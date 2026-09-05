-- Phase 3.2 Memory Extension Schema
-- Base: schema_v4.sql (memory, chunks_v4, code_graph, conversations)
-- Idempotent: safe to re-run via psql -f database/schema_v4_memory.sql

-- Metadata columns for memory chunks (LESSONS.md lessons)
ALTER TABLE memory ADD COLUMN IF NOT EXISTS source_file TEXT DEFAULT 'memory/LESSONS.md';
ALTER TABLE memory ADD COLUMN IF NOT EXISTS lesson_id TEXT;
ALTER TABLE memory ADD COLUMN IF NOT EXISTS tags TEXT[];
ALTER TABLE memory ADD COLUMN IF NOT EXISTS linked_chunk_id INTEGER;

-- Unique constraint for upsert on lesson_id (per source_file)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'memory_lesson_id_unique'
  ) THEN
    ALTER TABLE memory ADD CONSTRAINT memory_lesson_id_unique UNIQUE (lesson_id);
  END IF;
END $$;

-- Indexes for filtering
CREATE INDEX IF NOT EXISTS idx_memory_source_file ON memory(source_file);
CREATE INDEX IF NOT EXISTS idx_memory_lesson_id ON memory(lesson_id);
CREATE INDEX IF NOT EXISTS idx_memory_tags ON memory USING GIN (tags);

-- Relationship mapping: memory lesson → code chunks
CREATE TABLE IF NOT EXISTS memory_edges (
    id SERIAL PRIMARY KEY,
    from_memory_id INTEGER REFERENCES memory(id) ON DELETE CASCADE,
    to_chunk_id INTEGER,
    relation TEXT CHECK (relation IN ('implements', 'fixes', 'references')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_memory_edges_from ON memory_edges(from_memory_id);
CREATE INDEX IF NOT EXISTS idx_memory_edges_to ON memory_edges(to_chunk_id);

-- Note: embedding remains vector(768) via pgvector, stored as ::vector cast (asyncpg returns string)
-- Search stays exact brute-force for memory (no HNSW): SELECT ... ORDER BY embedding <=> $1::vector LIMIT $2
