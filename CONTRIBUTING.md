# Contributing

## Workflow
1. Create branch from `main`: `git checkout -b feat/short-name`
2. Keep working tree clean — do not mix unrelated changes (e.g. `.env.example` secrets, deleted `ai-dashboard/server.js` in same PR as dashboard work).
3. Commit with conventional commits: `feat:`, `fix:`, `chore:`, `docs:`
4. Push and open PR against `main` using the PR template. Ensure CI `verify` passes (`npm run lint`, `npm run build` in `ai-dashboard`).

## Local Setup
```bash
pip install -r requirements.txt
python sb.py status
cd ai-dashboard && npm ci && npm run lint && npm run build
docker compose up -d --build
```

## Secrets
- Copy `.env.example` (4 lines) to `.env` and fill real values locally. Never commit `.env`.
- Check before push: `git diff -- .env.example` should be empty or placeholder-only; `git status` clean except intended files.

## Code Style
- Python: `ruff` / `black` if configured
- TypeScript: `npm run lint` must pass
- Keep PRs small and scoped (Phase 2 dashboard ≠ env/config cleanups)
