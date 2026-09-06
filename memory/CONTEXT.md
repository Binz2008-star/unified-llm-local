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
