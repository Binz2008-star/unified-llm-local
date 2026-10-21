# Second Brain v4 — Agent Instructions (v5.0)

## Ground Truth (verified 2026-09-06; code claims re-verified 2026-10-21)

> **This checkout is a cold archive.** It lives at
> `C:\Users\loyal\pac-sources\unified-llm-local`, is on branch `master`, and has
> **no `.env`** — so tests and the Docker stack will not run here as written.
> The Second Brain MCP server is **not registered in the current global OpenCode
> config** (`~/.config/opencode/opencode.jsonc`), contrary to Rule 9 below.
> Verify runtime state before assuming anything is live.

### System Architecture
```
User → OpenCode (MCP) → mcp_server_v4.py → brain_agent_v4.py → Ollama + Neon DB
                                     ↕
                              Docker API (localhost:8000) — FastAPI
                                     ↕
                         second-brain-db (localhost:5432) — pgvector
```

### Runtime State
| Component | Where | Status | URL/Port |
|-----------|-------|--------|----------|
| FastAPI API | Docker `second-brain-v4` | 🟢 Running | `localhost:8000` |
| PostgreSQL | Docker `second-brain-db` | 🟢 Running | `localhost:5432` |
| Ollama | Host machine | 🟢 Running | `localhost:11434` |
| MCP Server | Local process (via OpenCode) | ⚪ Not configured (absent from global config as of 2026-10-21) | stdio |

### Database
| Table | Rows | Purpose |
|-------|------|---------|
| `chunks_v4` | 10,404 | Code chunks with HNSW embeddings (768-dim) |
| `code_graph` | 1,352 | File→file import edges |
| `memory` | 30 (per 2026-09-07 handoff — not re-verified) | Long-term lessons (seeded; was 0 on 2026-09-06) |
| `conversations` | 289 (per 2026-09-07 handoff — not re-verified) | Agent history, written by `save_conversation()` |
| `projects` | 3 | Registry |

### Ollama Models
| Model | Size | Purpose |
|-------|------|---------|
| `qwen2.5-coder:14b` | 9GB | Primary (agent, architect, editor) |
| `qwen2.5:7b` | 4.7GB | Fallback (32K ctx) |
| `deepseek-r1:14b` | 9GB | Reasoning tasks |
| `nomic-embed-text` | 274MB | 768-dim embeddings |

### Projects
| ID | Host Path | Container Path |
|----|-----------|----------------|
| `rico` | `X:\rico\Rico-Your-AI-intelligent-job-hunt-partner-in-the-UAE` | `/app/projects/rico` |
| `lvyy` | `C:\Users\loyal\lvyy-ai-sales-agent` | `/app/projects/lvyy` |
| `content-engine` | `X:\content engine\Robin-Content-Engine-v2` | `/app/projects/content-engine` |
| `second-brain` | `C:\Users\loyal\unified-llm-local` | `/app` |

## Code Map — Every File and What It Does

### Core Agent
| File | Lines | Purpose |
|------|-------|---------|
| `brain_agent_v4.py` | 1183 | Multi-agent orchestration (Researcher→Architect→Editor→Tester→Memory). Has `Agent` class, `search_brain()`, `run_multi_agent()`, `run_multi_agent_stream()`, all `tool_*` functions |
| `api.py` | 689 | FastAPI server. Endpoints: `/api/search`, `/api/chat`, `/api/agent`, `/api/agent/stream`, `/api/status`, `/api/projects`, `/api/memory`, `/api/system` |
| `sb.py` | 237 | CLI wrapper. Commands: `chat`, `agent`, `search`, `status`, `evolve`, `ui`, `switch`. `interactive_v4()` now exists (2026-09-07) — `chat` works |
| `mcp_server_v4.py` | 247 | MCP 2.x server. Tools: `search_brain`, `agent_task`, `get_status`, `list_memory`, `apply_patch`, `replace_block`. Calls `ba.tool_apply_patch` / `ba.tool_replace_block`, which exist in `brain_agent_v4.py` (2026-09-07) |

### Security Modules
| File | Lines | Purpose |
|------|-------|---------|
| `tool_security.py` | 526 | Central command executor. Allowlist (`ALLOWED_EXECUTABLES`), blocked args, `validate_command()`, `validate_path()`, `run_command()`, `read_file()`, `write_file()`, `apply_patch()`, `delete_file()`, `rename_file()`, `copy_file()`, audit log |
| `path_security.py` | 239 | `PathResolver` — traversal/symlink/absolute rejection, null byte detection, `.git` blocking |
| `git_security.py` | 354 | `SecureGit` — dangerous option blocking, malicious ref detection, env isolation |
| `protected_path_policy.py` | 319 | Protects `.env*`, `credentials.json`, `*.pem`, `*.key`, `id_rsa` from mutation. Secret content detection. `scrub_secrets()` |
| `merge_lock.py` | 403 | Cross-process mutual exclusion via atomic file lock. Lease TTL, stale recovery, re-entrant |
| `merge_gate.py` | 527 | 12-step merge verification pipeline. Baseline SHA → ancestry → security → fast-forward |
| `rollback.py` | 458 | Deterministic rollback via `git checkout --force`. Audit trail, untracked file safety, idempotent |
| `worktree.py` | 281 | Agent isolation via git worktrees. Agent never modifies primary repo directly |
| `test_evidence.py` | 253 | Frozen `TestEvidence` dataclass, `PolicyGate`, SHA-256 artifact integrity |
| `app_settings.py` | 112 | Pydantic-settings `Settings`. All env vars typed. Production safety validator |
| `http_session.py` | 145 | Shared aiohttp singleton. Connection pooling (10/5), retry with backoff, timeout |
| `context_builder.py` | 220 | Token-budget context (24K default), dedup, source attribution, deterministic ordering |

### Data Pipeline
| File | Lines | Purpose |
|------|-------|---------|
| `chunker_v4.py` | 536 | AST-aware chunking (Python `ast`, JS/TS `tree-sitter`). `CodeChunk` dataclass, `ASTChunker` class |
| `reindex_v4.py` | 688 | Full re-index pipeline. File discovery → chunk → embed → DB insert. Batch embedding with retry |
| `migrate_v4.py` | 217 | Schema migration v3→v4. Creates tables, `hybrid_search()` function, migrates chunks |
| `memory.py` | 262 | `MemoryManager` — file+Neon storage, fingerprint dedup, watchdog file watcher |
| `evolve.py` | 284 | Self-evolution. Analyzes failures, generates proposals, auto-applies to AGENTS.md |

### Config Files
| File | Purpose |
|------|---------|
| `.env` | **ACTIVE** — Neon DSN, Ollama URLs, model config, project paths |
| `.env.example` | Template with comments |
| `.env.prod` | Production template (placeholders) |
| `opencode.json` | OpenCode config — model, MCP servers, permissions |
| `pyproject.toml` | Python deps, pytest config |
| `ruff.toml` | Linter/formatter config |
| `schema_v4.sql` | DB schema (tables, HNSW index, `hybrid_search()` function) |

### Docker
| File | Purpose |
|------|---------|
| `docker-compose.v4.yml` | **ACTIVE** — db (pgvector) + ollama + second-brain-v4 (API) |
| `docker-compose.override.yml` | Dev override — uses host Ollama instead of containerized |
| `docker-compose.yml` | Production — second-brain + code-it-dashboard |
| `Dockerfile.v4` | Multi-stage Python 3.12 image for API |

### Tests
| File | Tests | What it covers |
|------|-------|----------------|
| `tests/test_tool_security.py` | 36 | Allowlist, path validation, command injection, file ops |
| `tests/test_security.py` | 30 | Path security, git security, shell injection, context builder, worktree, merge gate |
| `tests/test_merge_lock.py` | 22 | Atomic lock, ownership, TTL, stale recovery, cross-process |
| `tests/test_evidence.py` | 25 | Evidence model, persistence, PolicyGate, tool_security integration |
| `tests/test_rollback.py` | 34 | Clean/partial/idempotent rollback, untracked files, audit trail |
| `tests/test_sec05_protection.py` | 45 | Protected paths, secrets, traversal, content validation, scrubbing |
| `tests/test_app_settings.py` | 12 | Settings defaults, validation, production checks |
| `tests/test_benchmarks.py` | 5 | Performance gates (path resolve, command validate, file read) |
| `tests/test_memory_dedup.py` | 2 | Fingerprint normalization |
| `tests/test_failure_gate.py` | 1 | `_tool_result_failed()` helper |

### Docs
| File | Purpose |
|------|---------|
| `README.md` | Primary docs — features, quickstart, architecture |
| `AGENTS.md` | **This file** — agent ground truth |
| `HARDENING-PLAN.md` | Security audit + implementation plan |
| `TECHNICAL-ARCHITECTURE.md` | Detailed architecture + data flows |
| `memory/LESSONS.md` | Long-term lessons from agent runs |
| `memory/MEMORY.md` | User preferences + facts |
| `memory/CONTEXT.md` | Current project context |
| `memory/PATTERNS.md` | Cross-repo code patterns |

## Bug Status (verified 2026-10-21 — do not re-litigate)

All seven bugs from the 2026-09-06 list have been resolved or obsoleted.
Do **not** treat the old list as a to-do queue.

| # | 2026-09-06 claim | Status 2026-10-21 | Evidence |
|---|------------------|-------------------|----------|
| 1 | `sb.py` calls missing `interactive_v4()` | **FIXED** | `async def interactive_v4():` exists in `brain_agent_v4.py` |
| 2 | `ba.tool_apply_patch()` missing | **FIXED** | `def tool_apply_patch(...)` exists in `brain_agent_v4.py` |
| 3 | `ba.tool_replace_block()` missing | **FIXED** | `def tool_replace_block(...)` exists in `brain_agent_v4.py` |
| 4 | `opencode.json:74` MCP path wrong | **OBSOLETE** | No `opencode.json` in this repo; no second-brain server in the global config |
| 5 | Model mismatch | **UNVERIFIED** | No `.env` in this checkout, so it cannot be checked here |
| 6 | `memory` empty | **FIXED (per handoff)** | Seeded 30 rows on 2026-09-07; not re-verified |
| 7 | `conversations` empty | **FIXED (per handoff)** | 289 rows on 2026-09-07; written by `save_conversation()` |

Genuinely still open, from the 2026-09-07 handoff:
- `tool_apply_patch` on Windows hits a temp-file path issue in `tool_security.py` (works on Linux/macOS).
- `qwen2.5-coder:14b` can time out on slower hardware.

## Rules

1. **NEVER re-discover** — read this file first, not code
2. **search_brain first** — before answering about code, search the knowledge base
3. **Small diffs** — create small, testable changes
4. **Conventional commits** — `feat:`, `fix:`, `docs:`, `refactor:`
5. **Test after** — run `python -m pytest tests/ -q` after changes
6. **Ask before delete** — unless user explicitly said delete
7. **Security first** — all commands through `tool_security.run_command()`, never `shell=True`
8. **Docker is source of truth for runtime** — `docker exec second-brain-v4` to inspect running system
9. **Global config is source of truth for MCP** — `~/.config/opencode/opencode.jsonc` (V2 shape: `mcp.servers.<name>`), not a project `opencode.json`
10. **This checkout is cold** — do not run `pytest` or Docker expecting them to work without a restored `.env`

## Self-Evolution

After each task:
- What worked? → add to `memory/PATTERNS.md`
- What failed? → add to `memory/LESSONS.md`
- What did user prefer? → add to `memory/MEMORY.md`
- Update this file (AGENTS.md) with new findings

Last updated: 2026-10-21 (bug-status reconciliation; code claims re-verified)
