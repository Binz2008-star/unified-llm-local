# LESSONS — Deduplicated Knowledge Base

## Architecture

### Docker Is Source of Truth for Runtime
- The API runs inside Docker (`second-brain-v4` container), not locally
- Use `docker exec second-brain-v4` to inspect the running system
- Local Python is only for MCP server and CLI
- `.env` is NOT inside container — env vars come from `docker-compose.v4.yml` + `docker-compose.override.yml`

### Dual-Pool Database
- `LOCAL_DSN` → pgvector Docker (chunks_v4, code_graph) — vector search
- `NEON_DSN` → Neon Cloud (memory, conversations, projects) — metadata
- `search_brain()` only uses LOCAL_DSN (chunks). Memory/conversations on Neon are separate.

### Model Reality
- Container runtime uses `qwen2.5-coder:14b` (overridden from compose file)
- `.env` says `qwen2.5:7b` but container ignores it (env_file is `.env.prod` which has placeholders)
- opencode.json configures `qwen2.5-coder:14b` — matches container
- AGENTS.md previously said "NO qwen2.5-coder:14b pulled" — this was wrong. It IS pulled and running.

## Security

### Never Use shell=True
- All subprocess calls go through `tool_security.run_command()` which uses `asyncio.create_subprocess_exec`
- `shell=True` is rejected by CI grep gates
- `subprocess.run` is never used directly in production code

### Path Validation Is Mandatory
- Every file operation goes through `validate_path()` in `tool_security.py`
- Absolute paths, traversal (`../`), `.git/`, symlinks, null bytes — all rejected
- Protected files (`.env*`, `credentials.json`, `*.pem`, `*.key`) — mutation blocked

### Commands Go Through Allowlist
- `ALLOWED_EXECUTABLES`: python, pip, pytest, ruff, git, node, npm, cat, head, tail, etc.
- Blocked args: push, force, --hard, sudo, rm, format, etc.
- Shell metacharacters (`;`, `|`, `$`, `` ` ``) — rejected

## Development

### Test-Driven Changes
- Run `python -m pytest tests/ -q` after every change
- 289+ tests, ~45 seconds
- `ruff check .` for lint, `python -m compileall -q .` for syntax

### Git Workflow
- Branch: `feat/security-hardening` → merge to `master`
- Conventional commits: `feat:`, `fix:`, `docs:`, `refactor:`
- Never force-push, never commit secrets
- Two remotes: `origin` (GitHub), `second-brain-kb` (local backup)

### MCP Server Path
- Must point to `C:\Users\loyal\unified-llm-local\mcp_server_v4.py` (not `X:\second-brain-kb`)
- Python: global Python 3.12 (has asyncpg, aiohttp, fastapi, dotenv)
- The `.venv` in `X:\unified-llm-local` has MCP SDK — needed for `mcp_server_v4.py`

## Failures

### Gitleaks
- Historical Neon DSN (`npg_Iwmn6zQlT5Jt`) in git history at commits `eead02f` and `09bdbff`
- Deferred until project completion. Do NOT re-commit secrets.

### Container Chat Crashes
- API `/api/chat` returns `llama-server NTSTATUS` error
- Root cause: Ollama model server crashes on chat requests
- Workaround: Use search endpoint directly, or fix Ollama configuration

### Memory Table Empty
- `memory` table has 0 rows despite `MemoryManager` existing
- `save_conversation()` exists but isn't called by agent pipeline
- Need to seed from `memory/LESSONS.md` or wire into agent flow

## 2026-09-07 00:39 [lesson] second-brain
# MEMORY — User Facts & Preferences

## Identity
- **User**: loyal (GitHub: Binz2008-star)
- **Platform**: Windows (PowerShell), Python 3.12.10
- **Projects**: rico (job hunt AI), lvyy (AI sales agent), content-engine (Robin), second-brain (this)

## Preferences
- Wants everything to work in **terminal via OpenCode** — no web dashboard needed
- Requires actual commit SHAs, pytest exit codes, `git grep` evidence — not agent transcripts
- Prefers **small diffs, test after each change**
- Uses conventional commits: `feat:`, `fix:`, `docs:`
- Does NOT want unnecessary code explanation — just do the work
- Asks before deleting files (unless explicitly told to delete)

## System Facts
- **Docker containers run the API** (not local Python). `second-brain-v4` on `:8000`, `second-brain-db` on `:5432`
- **Ollama runs on host** (not in Docker). `host.docker.internal:11434` from containers
- **Model in use**: `qwen2.5-coder:14b` (9GB) — container runtime overrides compose file
- **Neon DSN** in `.env` and `opencode.json` — do NOT commit to git
- **Two copies existed**: `X:\unified-llm-local` (primary) and `C:\Users\loyal\unified-llm-local` (clone). Both synced to same commit.
- **`second-brain-kb` repo** on GitHub is the original. `unified-llm-local` has security hardening added.
- **Backup**: `X:\second-brain-kb-stale-backup-20260906-090013` exists (stale snapshot)

## Key Paths
- `C:\Users\loyal\unified-llm-local` — our working copy (this repo)
- `X:\unified-llm-local` — primary repo with .venv, pgdata, ollama_data
- `C:\Users\loyal\.config\opencode\opencode.json` — OpenCode MCP config
- `C:\Users\loyal\AppData\Local\Temp\opencode` — temp work directory


## 2026-09-07 00:39 [lesson] second-brain
# LESSONS — Deduplicated Knowledge Base

## Architecture

### Docker Is Source of Truth for Runtime
- The API runs inside Docker (`second-brain-v4` container), not locally
- Use `docker exec second-brain-v4` to inspect the running system
- Local Python is only for MCP server and CLI
- `.env` is NOT inside container — env vars come from `docker-compose.v4.yml` + `docker-compose.override.yml`

### Dual-Pool Database
- `LOCAL_DSN` → pgvector Docker (chunks_v4, code_graph) — vector search
- `NEON_DSN` → Neon Cloud (memory, conversations, projects) — metadata
- `search_brain()` only uses LOCAL_DSN (chunks). Memory/conversations on Neon are separate.

### Model Reality
- Container runtime uses `qwen2.5-coder:14b` (overridden from compose file)
- `.env` says `qwen2.5:7b` but container ignores it (env_file is `.env.prod` which has placeholders)
- opencode.json configures `qwen2.5-coder:14b` — matches container
- AGENTS.md previously said "NO qwen2.5-coder:14b pulled" — this was wrong. It IS pulled and running.

## Security

### Never Use shell=True
- All subprocess calls go through `tool_security.run_command()` which uses `asyncio.create_subprocess_exec`
- `shell=True` is rejected by CI grep gates
- `subprocess.run` is never used directly in production code

### Path Validation Is Mandatory
- Every file operation goes through `validate_path()` in `tool_security.py`
- Absolute paths, traversal (`../`), `.git/`, symlinks, null bytes — all rejected
- Protected files (`.env*`, `credentials.json`, `*.pem`, `*.key`) — mutation blocked

### Commands Go Through Allowlist
- `ALLOWED_EXECUTABLES`: python, pip, pytest, ruff, git, node, npm, cat, head, tail, etc.
- Blocked args: push, force, --hard, sudo, rm, format, etc.
- Shell metacharacters (`;`, `|`, `$`, `` ` ``) — rejected

## Development

### Test-Driven Changes
- Run `python -m pytest tests/ -q` after every change
- 289+ tests, ~45 seconds
- `ruff check .` for lint, `python -m compileall -q .` for syntax

### Git Workflow
- Branch: `feat/security-hardening` → merge to `master`
- Conventional commits: `feat:`, `fix:`, `docs:`, `refactor:`
- Never force-push, never commit secrets
- Two remotes: `origin` (GitHub), `second-brain-kb` (local backup)

### MCP Server Path
- Must point to `C:\Users\loyal\unified-llm-local\mcp_server_v4.py` (not `X:\second-brain-kb`)
- Python: global Python 3.12 (has asyncpg, aiohttp, fastapi, dotenv)
- The `.venv` in `X:\unified-llm-local` has MCP SDK — needed for `mcp_server_v4.py`

## Failures

### Gitleaks
- Historical Neon DSN (`npg_Iwmn6zQlT5Jt`) in git history at commits `eead02f` and `09bdbff`
- Deferred until project completion. Do NOT re-commit secrets.

### Container Chat Crashes
- API `/api/chat` returns `llama-server NTSTATUS` error
- Root cause: Ollama model server crashes on chat requests
- Workaround: Use search endpoint directly, or fix Ollama configuration

### Memory Table Empty
- `memory` table has 0 rows despite `MemoryManager` existing
- `save_conversation()` exists but isn't called by agent pipeline
- Need to seed from `memory/LESSONS.md` or wire into agent flow

## 2026-09-07 00:39 [lesson] second-brain
# MEMORY — User Facts & Preferences

## Identity
- **User**: loyal (GitHub: Binz2008-star)
- **Platform**: Windows (PowerShell), Python 3.12.10
- **Projects**: rico (job hunt AI), lvyy (AI sales agent), content-engine (Robin), second-brain (this)

## Preferences
- Wants everything to work in **terminal via OpenCode** — no web dashboard needed
- Requires actual commit SHAs, pytest exit codes, `git grep` evidence — not agent transcripts
- Prefers **small diffs, test after each change**
- Uses conventional commits: `feat:`, `fix:`, `docs:`
- Does NOT want unnecessary code explanation — just do the work
- Asks before deleting files (unless explicitly told to delete)

## System Facts
- **Docker containers run the API** (not local Python). `second-brain-v4` on `:8000`, `second-brain-db` on `:5432`
- **Ollama runs on host** (not in Docker). `host.docker.internal:11434` from containers
- **Model in use**: `qwen2.5-coder:14b` (9GB) — container runtime overrides compose file
- **Neon DSN** in `.env` and `opencode.json` — do NOT commit to git
- **Two copies existed**: `X:\unified-llm-local` (primary) and `C:\Users\loyal\unified-llm-local` (clone). Both synced to same commit.
- **`second-brain-kb` repo** on GitHub is the original. `unified-llm-local` has security hardening added.
- **Backup**: `X:\second-brain-kb-stale-backup-20260906-090013` exists (stale snapshot)

## Key Paths
- `C:\Users\loyal\unified-llm-local` — our working copy (this repo)
- `X:\unified-llm-local` — primary repo with .venv, pgdata, ollama_data
- `C:\Users\loyal\.config\opencode\opencode.json` — OpenCode MCP config
- `C:\Users\loyal\AppData\Local\Temp\opencode` — temp work directory



## 2026-09-07 00:40 [lesson] second-brain
# PATTERNS — Cross-Repo Code Patterns

## Agent Pipeline Pattern
```python
# Every agent task follows this flow:
1. search_brain(query) → context
2. Architect plans (uses context)
3. Editor writes code (uses plan + tools)
4. Tester runs tests (uses pytest)
5. Memory saves lessons (uses LESSONS.md)
```

## Tool Function Pattern
```python
# All tool functions follow this signature:
def tool_<name>(<args>, workspace: Path = None) -> str:
    """Returns human-readable result string."""
    # Validate inputs
    # Execute operation
    # Return result or error message
```

## Error Handling Pattern
```python
# Failure gate: N consecutive failures → abort
max_failures = _settings.max_consecutive_tool_failures  # default 3
consecutive_failures = 0
# On failure: consecutive_failures += 1, sleep, retry
# On success: consecutive_failures = 0
# If consecutive_failures >= max: return "[AGENT GAVE UP]"
```

## Security Pattern
```python
# Every file operation:
1. validate_path(file_path, workspace)  # bounds check
2. assert_mutation_allowed(path, operation)  # protected file check
3. Execute operation
4. Audit log entry
```

## Database Pattern
```python
# Dual-pool: local for vectors, Neon for metadata
pool = await _get_local_pool()  # pgvector Docker
async with pool.acquire() as conn:
    rows = await conn.fetch("SELECT ... FROM hybrid_search(...)")
```

## Docker Pattern
```python
# Container env vars override .env file
# docker-compose.v4.yml defines base
# docker-compose.override.yml overrides for dev (host Ollama)
# Runtime: docker exec second-brain-v4 env | grep MODEL
```

## Test Pattern
```python
# Unit tests: tmp_path fixture, no external deps
# Integration tests: real git repos, subprocess, DB connections
# Performance tests: throughput gates (ops/sec)
# Security tests: injection attempts, path traversal, etc.
```


## 2026-09-07 00:40 [lesson] second-brain
# CONTEXT — Current Project State

## What We're Building
An autonomous AI coding assistant that:
1. Indexes your code (AST-aware chunking, hybrid search)
2. Runs multi-agent coding tasks (search → plan → write → test → commit)
3. Self-evolves (learns from failures, improves itself)
4. Runs entirely in terminal via OpenCode MCP integration

## Current Sprint (Sep 2026)
**Goal**: Make the system run end-to-end from terminal via OpenCode.

### Done
- [x] Security hardening (11 modules: tool_security, path_security, git_security, etc.)
- [x] 289+ pytest tests passing
- [x] Docker containers running (API on :8000, DB on :5432)
- [x] 10,404 code chunks indexed across 3 projects
- [x] Hybrid search (RRF) working in PostgreSQL
- [x] CI/CD with benchmark gates
- [x] Merged second-brain-kb features into unified-llm-local

### In Progress
- [ ] Fix MCP server function references (apply_patch, replace_block)
- [ ] Fix opencode.json MCP path
- [ ] Make `sb.py chat` work
- [ ] Seed memory table from LESSONS.md
- [ ] Persist agent conversations

### Blocked
- Gitleaks CI failure (historical secret in git history — deferred until project completion)
- Neon credential rotation (deferred)

## Architecture Decision: Docker vs Local
**Decision**: Docker containers run the API. Local Python runs MCP server + CLI.
**Why**: Container provides isolation, health checks, auto-restart. Local provides OpenCode integration.

## Model Configuration
| Setting | Value | Source |
|---------|-------|--------|
| Agent model | `qwen2.5-coder:14b` | Container runtime |
| Embed model | `nomic-embed-text` | .env |
| Embed dim | 768 | .env |
| Fallback model | `qwen2.5:7b` | .env |
| Reasoning model | `deepseek-r1:14b` | Available on host |


## 2026-09-07 00:56 [lesson] rico
Task: list files in current directory
Plan: {
  "name": "run_shell",
  "arguments": {
    "command": "ls"
  }
}
Result: {"name": "run_shell", "arguments": {"command": "ls"}}

## 2026-09-06 21:40 [lesson] rico
Task: hi
Plan: [AGENT GAVE UP] 3 consecutive model failures (cap 3); last: model qwen2.5-coder:14b call failed (TimeoutError: ). Ollama qwen2.5-coder:14b appears unavailable/hung (deepseek→qwen hang guard). Check `ollama ps` and `ollama list`, ensure qwen2.5:7b is pulled and VRAM free.
Result: [AGENT GAVE UP] 3 consecutive model failures (cap 3); last: model qwen2.5-coder:14b call failed (TimeoutError: ). Ollama qwen2.5-coder:14b appears unavailable/hung (deepseek→qwen hang guard). Check `ollama ps` and `ollama list`, ensure qwen2.5:7b is pulled and VRAM free.
