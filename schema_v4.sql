
-- Enable extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Projects table
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    path TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enhanced chunks with hybrid search + code graph
CREATE TABLE IF NOT EXISTS chunks_v4 (
    id SERIAL PRIMARY KEY,
    project_id TEXT REFERENCES projects(id),
    file_path TEXT NOT NULL,
    chunk_index INT NOT NULL,
    chunk_type TEXT NOT NULL DEFAULT 'generic', -- function, class, import, generic
    chunk_name TEXT, -- function/class name
    content TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    language TEXT,
    start_line INT,
    end_line INT,
    -- Vectors
    embedding vector(768) NOT NULL,
    -- Hybrid search: tsvector for keyword
    content_tsv tsvector GENERATED ALWAYS AS (to_tsvector('english', content)) STORED,
    -- Code graph
    imports TEXT[], -- extracted imports
    calls TEXT[], -- function calls
    -- Metadata
    indexed_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(project_id, file_path, chunk_index)
);

-- Code graph edges (file -> file dependencies)
CREATE TABLE IF NOT EXISTS code_graph (
    id SERIAL PRIMARY KEY,
    project_id TEXT REFERENCES projects(id),
    source_file TEXT NOT NULL,
    target_file TEXT NOT NULL,
    relation TEXT NOT NULL, -- imports, calls, extends
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Conversations memory (agent learns)
CREATE TABLE IF NOT EXISTS conversations (
    id SERIAL PRIMARY KEY,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL, -- user, assistant, tool
    content TEXT NOT NULL,
    tool_calls JSONB,
    project_id TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Long-term memory / lessons
CREATE TABLE IF NOT EXISTS memory (
    id SERIAL PRIMARY KEY,
    type TEXT NOT NULL, -- pattern, lesson, preference, fact
    content TEXT NOT NULL,
    project_id TEXT,
    embedding vector(768),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for hybrid search
CREATE INDEX IF NOT EXISTS idx_chunks_v4_embedding ON chunks_v4 USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
CREATE INDEX IF NOT EXISTS idx_chunks_v4_tsv ON chunks_v4 USING GIN (content_tsv);
CREATE INDEX IF NOT EXISTS idx_chunks_v4_trgm ON chunks_v4 USING GIN (content gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_chunks_v4_project ON chunks_v4 (project_id, file_path);
-- NOTE: no ANN index on memory - it's small and HNSW gave unreliable approximate recall
CREATE INDEX IF NOT EXISTS idx_conversations_session ON conversations (session_id, created_at);

-- Hybrid search function (RRF - Reciprocal Rank Fusion)
-- Better than linear scoring: no normalization needed, robust to outliers, parameter-free
CREATE OR REPLACE FUNCTION hybrid_search(
    query_text TEXT,
    query_embedding vector(768),
    match_count INT DEFAULT 10,
    rrf_k INT DEFAULT 60
) RETURNS TABLE (
    id INT,
    project_id TEXT,
    file_path TEXT,
    chunk_name TEXT,
    content TEXT,
    similarity FLOAT,
    rank FLOAT
) LANGUAGE plpgsql STABLE PARALLEL SAFE AS $$
DECLARE
    kw tsquery;
    candidate_k INT;
BEGIN
    -- Prepare full-text search query
    kw := websearch_to_tsquery('english', query_text);
    IF kw IS NULL OR kw = ''::tsquery THEN
        kw := plainto_tsquery('english', query_text);
    END IF;

    candidate_k := GREATEST(match_count * 8, 50);

    RETURN QUERY
    WITH vec_cand AS (
        -- 1. Rank top vector matches by order
        SELECT 
            v.id,
            (1 - (v.embedding <=> query_embedding))::FLOAT AS vec_sim,
            ROW_NUMBER() OVER (ORDER BY v.embedding <=> query_embedding) AS vec_rank
        FROM chunks_v4 v
        ORDER BY v.embedding <=> query_embedding
        LIMIT candidate_k
    ),
    kw_cand AS (
        -- 2. Rank top keyword matches by order
        SELECT 
            k.id,
            ROW_NUMBER() OVER (ORDER BY ts_rank_cd(k.content_tsv, kw) DESC) AS kw_rank
        FROM chunks_v4 k
        WHERE k.content_tsv @@ kw
        ORDER BY ts_rank_cd(k.content_tsv, kw) DESC
        LIMIT candidate_k
    ),
    combined AS (
        -- 3. Merge candidates and compute RRF score: 1/(k + rank)
        SELECT 
            COALESCE(v.id, k.id) AS cand_id,
            COALESCE(v.vec_sim, (1 - (c.embedding <=> query_embedding))::FLOAT) AS vec_sim,
            (
                COALESCE(1.0 / (rrf_k + v.vec_rank), 0.0) + 
                COALESCE(1.0 / (rrf_k + k.kw_rank), 0.0)
            )::FLOAT AS rrf_score
        FROM vec_cand v
        FULL OUTER JOIN kw_cand k ON v.id = k.id
        JOIN chunks_v4 c ON c.id = COALESCE(v.id, k.id)
    )
    SELECT
        c.id,
        c.project_id,
        c.file_path,
        c.chunk_name,
        c.content,
        cb.vec_sim AS similarity,
        cb.rrf_score AS rank
    FROM combined cb
    JOIN chunks_v4 c ON c.id = cb.cand_id
    ORDER BY cb.rrf_score DESC
    LIMIT match_count;
END;
$$;
