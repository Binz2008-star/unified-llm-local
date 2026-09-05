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

## Dual-Pool Architecture (v4.1+)

Second Brain v4.1+ splits storage across two PostgreSQL instances:

```
┌─────────────────────────────────────────────────────────────────┐
│                    Second Brain v4.1+                           │
├─────────────────────────────────────────────────────────────────┤
│  LOCAL POOL (pgvector via Docker)          │  NEON POOL (Cloud) │
│  ───────────────────────────────           │  ─────────────────  │
│  LOCAL_DSN → localhost:5432                │  NEON_DSN → Cloud   │
│                                            │                     │
│  • chunks_v4 (10,404 rows, HNSW)           │  • memory (17 rows) │
│  • code_graph (1,352 edges)                │  • bugs (new)       │
│  • Vector search (HNSW, m=16)              │  • conversations    │
│  • Keyword search (tsvector + trigram)     │  • projects         │
└─────────────────────────────────────────────────────────────────┘
```

**Routing Logic:**
| Operation | Pool | Tables |
|-----------|------|--------|
| `search_brain()` | Local | `chunks_v4` |
| `agent_task` (code search) | Local | `chunks_v4`, `code_graph` |
| `save_conversation()` | Neon | `conversations` |
| `memory_mgr` (lessons/patterns) | Neon | `memory` |
| `bug_*` MCP tools | Neon | `bugs` |
| `bug_scan()` chunks search | Local | `chunks_v4` |
| `bug_scan()` bug creation | Neon | `bugs` |

**Benefits:**
- Large vector index (10K+ chunks, 768-dim) stays local — fast, free, no egress
- Small metadata tables (memory, bugs, conversations) centralized on Neon for multi-machine sync
- HNSW index only on local pool (Neon pool too small to benefit)

## Model Configuration (Corrected v4.1)

**Runtime Reality:** Ollama serves `qwen2.5:7b` (4.7 GB, 32K context), `deepseek-r1:14b` (9 GB, 128K context), `nomic-embed-text` (274 MB). **No `qwen2.5-coder:14b` is pulled.**

```env
# .env (local runtime)
OLLAMA_EMBED_URL=http://127.0.0.1:11434/api/embed
OLLAMA_CHAT_URL=http://127.0.0.1:11434/api/chat
ARCHITECT_MODEL=qwen2.5:7b
EDITOR_MODEL=qwen2.5:7b
CHAT_MODEL=qwen2.5:7b
EMBED_MODEL=nomic-embed-text
LOCAL_DSN=postgresql://postgres:password@localhost:5432/second_brain
NEON_DSN=postgresql://neondb_owner:...@ep-empty-paper-.../neondb?sslmode=require
```

**All context budgets sized for 32K (qwen2.5:7b), not 128K.**

## RAG Pipeline Audit (v4.1 — Sep 2026)

### P0 (Immediate — Wire Before Re-index)
1. **Hybrid Search Wiring** — `hybrid_search()` RRF exists in Postgres but `search_brain()` calls vector-only. Wire `search_brain()` → `hybrid_search()` + add SQL-side `project_id`/`language`/`chunk_type` filters.
2. **Token-Budget Context Builder** — Replace `.content[:800]` slice with budget-aware builder (dedup, attribution, 32K model budget).

### P1 (Before Next Re-index)
3. **Cleaning** — Purge stale/noise (playwright-report, archive dirs, package-lock.json, minified/generated files, license headers). Add `should_index()` gate + delete stale rows on every run.
4. **Chunking v2** — Token-capped (512 tok code / 800 doc / 1000 config), fix TS/TSX AST (2,259 stale chunks), split monoliths (>2000 tokens), full re-index.
5. **Eval Expansion** — 15-20 goldens (add symbol lookup, error-string, cross-project, TS symbols), auto-run `--hybrid` after every re-index, fail if Recall@3 < 1.0 or MRR < 0.85.

### P2
6. **Incremental Ingest** — Add `last_modified` to `chunks_v4`, diff-driven re-index (sha256 vs `content_hash`), optionally index `second-brain` itself.

### P3
7. **Rerank** — `bge-reranker-v2-m3` (2.5GB VRAM) top-50→8, behind env flag, eval A/B.
8. **Embed Batch** — BATCH 16→64, query embedding cache. Embedder swap (bge-m3) only if full re-embed accepted.

---

## Known Limitations (Updated)

1. **Model**: Runtime uses `qwen2.5:7b` (32K ctx), not `qwen2.5-coder:14b` (128K). All budgets sized for 32K.
2. **Chat timeout**: `qwen2.5:7b` fast (~10-30s); `OLLAMA_TIMEOUT=300` default.
3. **No HNSW on Neon `memory`**: Exact search (table < 100 rows).
4. **Tree-sitter fallback**: TS/TSX currently generic — fix via re-index (P1-4).
5. **No auth on API**: CORS `*` for local dev only.
6. **Windows paths**: Hardcoded in `.env`; use env vars for portability.
7. **Dual-pool sync**: Local pgvector must be running for code search; Neon for memory/bugs.
8. **Two divergent copies**: `X:\unified-llm-local` (git) vs `X:\second-brain-kb` (live) — sync before builds.

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