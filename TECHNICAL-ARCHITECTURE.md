# Technical Architecture — Second Brain v4

## System Overview

Second Brain v4 is a local-first, self-evolving code knowledge base with:
- **Hybrid semantic search** (vector + keyword + graph)
- **Multi-agent coding automation** (Researcher→Architect→Editor→Tester→Memory)
- **Long-term memory** with file + database persistence
- **Self-evolution** via failure analysis and AGENTS.md updates

## Component Diagram

```
┌─────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│   User / CLI    │────▶│    sb.py         │────▶│  brain_agent_v4  │
│   (sb chat/     │     │  (argparse)      │     │  (multi-agent)   │
│    agent/search)│     └──────────────────┘     └────────┬─────────┘
└─────────────────┘                                        │
                                                           │
                          ┌──────────────────┐             │
                          │    api.py        │             │
                          │  (FastAPI)       │◀────────────┤
                          │  /search         │             │
                          │  /chat           │             │
                          │  /agent          │             │
                          │  /agent/stream   │             │
                          │  /memory         │             │
                          └────────┬─────────┘             │
                                   │                       │
                    ┌──────────────┼──────────────┐       │
                    ▼              ▼              ▼       ▼
            ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐
            │ search_brain│ │  embed()   │ │ save_conv  │ │  memory.py │
            │ (hybrid)   │ │ (Ollama)   │ │ (Neon)     │ │ (files+DB) │
            └─────┬──────┘ └─────┬──────┘ └─────┬──────┘ └─────┬──────┘
                  │              │              │              │
                  ▼              ▼              ▼              ▼
            ┌────────────────────────────────────────────────────────┐
            │              Neon PostgreSQL (pgvector)                │
            │  chunks_v4  │  code_graph  │  memory  │  conversations │
            └────────────────────────────────────────────────────────┘
```

## Data Flow

### 1. Indexing (`reindex_v4.py`)
```
Source Files → ASTChunker.chunk() → CodeChunk[] → embed_batch() → 
DELETE old + INSERT new → chunks_v4 (embedding, content_tsv) → 
extract_imports() → code_graph edges
```

### 2. Search (`search_brain`)
```
Query → embed() → vector → hybrid_search(query, vector, top_k) → 
UNION(vector_top_k, keyword_top_k) → 
rank = 0.7*similarity + 0.3*normalized_ts_rank → ORDER BY rank
```

### 3. Multi-Agent Task (`run_multi_agent`)
```
Task → Researcher: search_brain(task) → brain_context
     → Architect: plan = chat(brain_context + task, tools=[search, read, shell])
     → Editor: impl = chat(plan + brain_context, tools=[read, write, shell])
     → Tester: test = chat(impl + plan, tools=[run_tests, lint, typecheck])
     → Memory: lesson = embed(task+plan+test) → add_memory("lesson", lesson)
     → Git: git_status() → git_commit() if changes
     → Conversations: OUTCOME row saved
```

### 4. SSE Streaming (`run_multi_agent_stream`)
```
Yields: {type: "start", session_id, task}
       {type: "phase", phase, status, message, data?}
       {type: "warning", message}
       {type: "complete", session_id, task, message}
```

### 5. Self-Evolution (`evolve.py`)
```
analyze_failures() → SELECT FROM conversations WHERE regex(failure_patterns)
evolve_tools() → pattern match failures → fixes[]
generate_improvements() → static list of known improvements
apply_proposals() → insert into AGENTS.md "### Not done / next" section
```

## Database Schema

### chunks_v4 (9,511 rows)
```sql
id SERIAL PK
project_id TEXT FK → projects(id)
file_path TEXT
chunk_index INT
chunk_type TEXT  -- function, class, import, generic
chunk_name TEXT  -- function/class name
content TEXT
content_hash TEXT (SHA256)
language TEXT
start_line INT
end_line INT
embedding vector(768)  -- HNSW index
content_tsv tsvector  -- GIN index (generated)
imports TEXT[]
calls TEXT[]
indexed_at TIMESTAMPTZ
UNIQUE(project_id, file_path, chunk_index)
```

### code_graph (1,352 rows)
```sql
id SERIAL PK
project_id TEXT FK
source_file TEXT
target_file TEXT
relation TEXT  -- imports, calls, extends
created_at TIMESTAMPTZ
```

### memory (1 row + growing)
```sql
id SERIAL PK
type TEXT  -- pattern, lesson, preference, fact
content TEXT
project_id TEXT
embedding vector(768)  -- NO HNSW (exact search)
created_at TIMESTAMPTZ
updated_at TIMESTAMPTZ
```

### conversations (9 rows + growing)
```sql
id SERIAL PK
session_id TEXT  -- uuid per multi-agent run
role TEXT  -- user, assistant, tool
content TEXT
tool_calls JSONB
project_id TEXT
created_at TIMESTAMPTZ
```

### projects (4 rows)
```sql
id TEXT PK  -- content-engine, lvyy, rico, second-brain
name TEXT
path TEXT
created_at TIMESTAMPTZ
updated_at TIMESTAMPTZ
```

## Hybrid Search Function (RRF - Reciprocal Rank Fusion)

```sql
CREATE OR REPLACE FUNCTION hybrid_search(
    query_text TEXT,
    query_embedding vector(768),
    match_count INT DEFAULT 10,
    rrf_k INT DEFAULT 60
) RETURNS TABLE (id, project_id, file_path, chunk_name, content, similarity, rank)
```
- **Keyword query**: `websearch_to_tsquery` (supports OR, phrases, implicit AND) with fallback to `plainto_tsquery`
- **Vector candidates**: Top `candidate_k = GREATEST(match_count * 8, 50)` via HNSW index, ranked by cosine distance
- **Keyword candidates**: Top `candidate_k` via GIN index, ranked by `ts_rank_cd`
- **Fusion**: Reciprocal Rank Fusion `1/(k + rank_vec) + 1/(k + rank_kw)` — no normalization needed, robust to outliers, parameter-free
- **Default `rrf_k = 60`** (empirically strong for code search)
- **Result**: Best of both semantic and lexical matching, ordered by combined RRF score

## AST Chunking Strategy

### Python (`ast` module)
- Imports → single chunk
- Classes → chunk per class (split methods if > 1.5× max_chars)
- Functions → chunk per function (split with overlap if > max_chars)
- Fallback: generic line-based chunker

### JavaScript/TypeScript (`tree-sitter`)
- Imports → single chunk
- Functions/Arrow functions/Methods → chunk per function
- Classes/Interfaces → chunk per class (recurse into methods)
- Large chunks split with overlap

### Generic (other languages)
- Line-based with natural break points (}, ), ], ```, ---)
- 3-line overlap between chunks

## Memory System

### File Storage (`./memory/`)
| File | Purpose | Neon Sync |
|------|---------|-----------|
| MEMORY.md | User identity, preferences | fact/preference |
| PATTERNS.md | Cross-repo code patterns | pattern |
| LESSONS.md | Failures, fixes, discoveries | lesson |
| CONTEXT.md | Current project context | fact |

### Neon `memory` Table
- Embeddings stored ONLY when `embedding` parameter provided
- No HNSW index (table small, exact brute-force is faster + accurate)
- Search: `ORDER BY embedding <=> query_vector LIMIT k`

### File Watcher
- `watchdog.Observer` on `./memory/` directory
- Debounced (500ms) to avoid duplicate events
- Calls `on_reload(name, path)` callback
- Shared observer instance to prevent leaks

## Self-Evolution Loop

```
1. sb evolve → analyze_failures()
   └─> SELECT FROM conversations WHERE content ~* failure_regex
   
2. evolve_tools()
   └─> Pattern match: "File not found" → "Improve path resolution"
       "embedding + vector" → "Check EMBED_DIM consistency"
       "timeout" → "Increase timeout, add retry"
   └─> Append to LESSONS.md
   └─> EACH fix → embed(fix) → INSERT INTO memory(type='lesson')

3. generate_improvements()
   └─> Static list: TS/JS AST, auto-embed, SSE, auto-commit, file watcher

4. apply_proposals()
   └─> Read AGENTS.md → find "### Not done / next"
   └─> Insert new proposals (idempotent)
```

## MCP Server (`mcp_server_v4.py`)

```python
Server("second-brain-v4", on_list_tools=..., on_call_tool=...)
```

| Tool | Description | Backend |
|------|-------------|---------|
| `search_brain` | Hybrid search across all projects | `ba.search_brain()` |
| `agent_task` | Run multi-agent pipeline | `ba.run_multi_agent()` |
| `get_status` | DB counts, projects, models | `_status_payload()` |
| `list_memory` | Long-term memories from Neon | `_memory_payload()` |

Registered in OpenCode via `opencode.json`:
```json
{
  "mcpServers": {
    "second-brain-v4": {
      "command": "python",
      "args": ["X:/second-brain-kb/mcp_server_v4.py"]
    }
  }
}
```

## Docker Deployment

```yaml
# docker-compose.v4.yml
services:
  second-brain-v4:
    build: { context: ., dockerfile: Dockerfile.v4 }
    env_file: .env
    environment:
      - OLLAMA_EMBED_URL=http://host.docker.internal:11434/api/embed
      - OLLAMA_CHAT_URL=http://host.docker.internal:11434/api/chat
    volumes:
      - ${PROJECT_CONTENT_ENGINE_HOST}:/app/projects/content-engine:ro
      - ${PROJECT_LVYY_HOST}:/app/projects/lvyy:ro
      - ${PROJECT_RICO_HOST}:/app/projects/rico:ro
      - ./memory:/app/memory
      - ./logs:/app/logs
      - ./ui:/app/ui:ro
    ports: ["8000:8000"]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/status"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
```

### Dockerfile
```dockerfile
FROM python:3.11-slim
RUN apt-get update && apt-get install -y git curl
COPY requirements.txt . && pip install -r requirements.txt
RUN pip install fastapi uvicorn python-multipart jinja2
COPY api.py brain_agent_v4.py memory.py .
COPY v4-extract/second-brain-v4/chunker_v4.py v4-extract/second-brain-v4/
COPY ui/ ui/
RUN mkdir -p /app/memory /app/logs /app/ui /app/v4-extract/second-brain-v4 /app/projects
EXPOSE 8000
CMD ["python", "api.py"]
```

## Configuration

### Environment Variables (`.env`)
```env
# Database
NEON_DSN=postgresql://user:pass@host/db?sslmode=require

# Ollama (local)
OLLAMA_EMBED_URL=http://127.0.0.1:11434/api/embed
OLLAMA_CHAT_URL=http://127.0.0.1:11434/api/chat

# Models (only deepseek-r1:14b + nomic-embed-text available locally)
ARCHITECT_MODEL=deepseek-r1:14b
EDITOR_MODEL=deepseek-r1:14b
CHAT_MODEL=deepseek-r1:14b
EMBED_MODEL=nomic-embed-text

# Projects
CURRENT_PROJECT=lvyy
PROJECT_CONTENT_ENGINE=X:\content engine\Robin-Content-Engine-v2
PROJECT_LVYY=C:\Users\loyal\lvyy-ai-sales-agent
PROJECT_RICO=X:\rico\Rico-Your-AI-intelligent-job-hunt-partner-in-the-UAE

# MCP
SECOND_BRAIN_AGENTS_MD=C:\Users\loyal\.config\opencode\AGENTS.md
```

## Known Limitations

1. **Single model**: Only `deepseek-r1:14b` available locally for all agents
2. **Chat timeout**: deepseek-r1:14b slow (~2-5 min); 600s timeout + retries
3. **No HNSW on `memory`**: Exact search (table < 100 rows)
4. **Tree-sitter fallback**: Falls back to generic chunker on parse errors
5. **No auth on API**: CORS `*` for local dev only
6. **Windows paths**: Hardcoded in `.env`; use env vars for portability

## Performance

| Metric | Value |
|--------|-------|
| Search latency (warm) | 235-260ms |
| Chunks indexed | 9,511 |
| Code graph edges | 1,352 |
| Memory entries | 1+ |
| Conversations per run | 8 rows |
| Embedding dim | 768 (nomic-embed-text) |
| Vector index | HNSW (m=16, ef_construction=64) |