# Changelog — Second Brain v4

## v4.0.0 (2026-09-02) — Full Upgrade Complete

### Phase 1: Schema & Data Migration ✅
- Migrated 651 v3 chunks → `chunks_v4` with hybrid search schema
- Added tables: `projects`, `code_graph`, `conversations`, `memory`
- `hybrid_search()` function: **RRF (Reciprocal Rank Fusion)** — `1/(k+rank_vec) + 1/(k+rank_kw)` with `rrf_k=60`
- Indexes: HNSW (m=16, ef_construction=64), GIN tsvector, trigram
- Latency: 235-260ms warm, <300ms baseline

### Phase 2: AST Chunking & Re-indexing ✅
- **9,511 chunks** across 3 projects (rico 7,750 / content-engine 1,541 / lvyy 220)
- **Python AST chunking**: functions, classes, imports as separate chunks
- **JavaScript/TypeScript AST chunking**: tree-sitter (functions, classes, interfaces, imports)
- **Code graph**: 1,352 import edges
- Excluded noise: lockfiles, generated dirs, test dirs (8,028 chunks purged)
- HNSW index for recall + latency

### Phase 3: Multi-Agent System ✅
- `brain_agent_v4.py`: Researcher → Architect → Editor → Tester → Memory
- All agents use local `deepseek-r1:14b` (only model available)
- `search_brain()`: asyncpg pool + retries + vector fallback
- `MemoryManager`: Markdown files + Neon persistence (embedding required)
- Conversations table populated per run (8 rows: context + 3 agents + OUTCOME)
- **Tester hardening**: Added `run_tests`, `lint`, `typecheck` tools + strict prompt

### Phase 4: CLI + API + Web UI + Docker ✅
- **`sb.py` + `sb.bat`**: `chat` / `agent` / `search` / `status` / `evolve` / `switch` / `ui`
- **`api.py`**: FastAPI on :8000 with CORS
  - `POST /search`, `POST /chat`, `POST /agent`, `GET /agent/stream` (SSE)
  - `GET /status`, `GET /projects`, `GET/POST /memory`
- **`ui/index.html`**: Search, chat, streaming agent, memory browser, status dashboard
- **`docker-compose.v4.yml` + `Dockerfile.v4`**: Health checks, env-based volumes

### Phase 5: Self-Evolution ✅
- `evolve.py`: Analyzes failures → generates `EVOLVE_TODO.md`
- Auto-embeds lessons to Neon `memory` table (searchable)
- Auto-applies proposals to `AGENTS.md` (idempotent, non-destructive)

### Phase 6: MCP Integration ✅
- `mcp_server_v4.py`: MCP 2.x low-level Server API
- Tools: `search_brain`, `agent_task`, `get_status`, `list_memory`
- Registered in OpenCode, verified live in this session

---

## Remaining Polish Items (Documented in UPGRADE-PLAN-v4.md)
- [ ] Option to run Ollama/Postgres inside Docker
- [ ] Streaming for agent tool calls in Web UI (partial - SSE for phases works)
- [ ] Auto-commit after successful task (implemented in `run_multi_agent`)
- [ ] File watcher for MEMORY.md auto-reload (implemented in `memory.py`)

---

## Verified 2026-09-02
- `conversations` table: 8 rows per multi-agent run
- OpenCode picks up MCP server tools
- Docker build + API + UI + search all working
- `sb status` / `sb search` / `sb evolve` all functional