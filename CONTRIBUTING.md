# Contributing

## Workflow
1. Create branch from `main`: `git checkout -b feat/short-name`
2. Keep working tree clean — do not mix unrelated changes (e.g. `.env.example` secrets, deleted `ai-dashboard/server.js` in same PR as dashboard work).
3. Commit with conventional commits: `feat:`, `fix:`, `chore:`, `docs:`
4. Push and open PR against `main` using the PR template. Ensure CI `verify` passes (`npm run lint`, `npm run build` in `ai-dashboard`).

## Local Setup (Perfect System)
```bash
# One-command setup (venv + deps + ollama check + env template)
make setup
# or manual:
pip install -r requirements.txt
pip install ruff pytest
ollama pull qwen2.5:7b && ollama pull nomic-embed-text
cp .env.example .env  # now 20+ vars (was 4) — fill NEON_DSN/LOCAL_DSN
python sb.py status   # → chunks 9577 / memory 17
cd ai-dashboard && npm ci && npm run lint && npm run build
docker compose -f docker-compose.v4.yml up -d --build
```

## Secrets (Dual-Pool)
- `.env` (Neon + LOCAL_DSN) and `.env.prod` (Docker) are gitignored — never commit real values. Use `.env.example` / `.env.prod.example` as templates (now 20 vars, not 4).
- Check before push: `git diff -- .env.example` placeholder-only; `git status` clean.
- GitHub Secrets needed only for push: `GHCR_TOKEN` (+ `NEON_DSN` if you want CI to run golden against real DB). Build `lint/test/build` is green without secrets.

## Code Style & Tests
- Python: `ruff check` + `ruff format` (see `ruff.toml`, `pyproject.toml`) — `make lint`
- Tests: `pytest -q` (memory dedup, failure gate) + `eval/run_golden.py` (12/12, Recall@3 100% MRR≥0.85) — `make test`
- TypeScript: `npm run lint` in `ai-dashboard` must pass
- Keep PRs small and scoped (Phase 2 dashboard ≠ env/config cleanups)
- Pre-commit: `pip install pre-commit && pre-commit install` (runs ruff on commit)
