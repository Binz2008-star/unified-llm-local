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
