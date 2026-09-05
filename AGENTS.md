# Unified LLM Agent — Evolving Instructions (v4.1)

## Current Context (auto-updated)

## Projects
- content-engine: X:\content engine\Robin-Content-Engine-v2
- lvyy: C:\Users\loyal\lvyy-ai-sales-agent
- rico: X:\rico\Rico-Your-AI-intelligent-job-hunt-partner-in-the-UAE
- second-brain: X:\unified-llm-local (git) — sync with X:\second-brain-kb (live MCP) before builds

## System State (v4.1 — Sep 2026)
- **Dual-Pool**: LOCAL_DSN (pgvector Docker: chunks_v4 10,404 / code_graph 1,352) + NEON_DSN (Neon Cloud: memory 17 / bugs / conversations)
- **Models**: qwen2.5:7b (32K ctx, primary), deepseek-r1:14b (128K, reasoning), nomic-embed-text (768-dim)
- **Ollama**: qwen2.5:7b (4.7GB) + deepseek-r1:14b (9GB) + nomic-embed-text (274MB) — NO qwen2.5-coder:14b pulled
- **Dual-Pool Routing**: search_brain/chunks→local, memory/bugs/conversations→neon, bug_scan chunks→local + bugs→neon
- **Docker**: docker-compose.override.yml (local pgvector + API on :8000, Dashboard :3000)

## Learned Patterns
- Dual-pool split: vector search local, metadata on Neon
- Fingerprint dedup on memory (content_hash) saves Ollama calls
- Failure gate N=3 prevents deepseek/qwen hangs
- Golden eval (12 queries) is regression gate for re-index
- Bug tracker MCP tools scan local chunks → create bugs on Neon

## Lessons
- Two divergent copies (X:\unified-llm-local git vs X:\second-brain-kb live) — MUST sync before any build
- Model premise was wrong: runtime is qwen2.5:7b (32K), not qwen2.5-coder:14b (128K)
- TS/TSX chunks are generic (stale) — need re-index after tree-sitter fix
- Hybrid_search exists in Postgres but not wired in search_brain() — P0
- Context builder needs token budget + dedup + attribution — P0

## Rules (evolve these as you learn):
1. ALWAYS search_brain first before answering about code
2. Switch project when task mentions different repo
3. Create small diffs, test after
4. Update MEMORY.md when you learn user preference
5. If tool fails 2x, try alternative approach
6. Ask before deleting files (unless user said delete)
7. Commit with conventional commits: feat:, fix:, docs:
8. **Sync git repo (X:\unified-llm-local) with live (X:\second-brain-kb) before any build**
9. **All context budgets sized for 32K (qwen2.5:7b), not 128K**

## Self-Evolution
- After each task, reflect: what worked, what didn't?
- If you notice repeated pattern, add to PATTERNS.md
- If you fail, add to LESSONS.md
- You can rewrite your own tools in brain-agent-v4.py if needed (self-evolution)

## Current Audit Priorities (v4.1 — Sep 2026)

### P0 (Wire Now — Before Re-index)
- [ ] Wire `hybrid_search()` RRF into `search_brain()` + SQL-side filters (project_id, language, chunk_type)
- [ ] Token-budget context builder (dedup, attribution, 32K budget)

### P1 (Before Next Re-index)
- [ ] Cleaning: purge stale/noise + license/minified/generated rejection
- [ ] Chunking v2: token-capped (512 tok code / 800 doc), fix TS/TSX AST, split monoliths, full re-index
- [ ] Eval expansion: 15-20 goldens, auto-run --hybrid after re-index, CI gate (Recall@3=100%, MRR>0.85)

### P2
- [ ] Incremental ingest: last_modified + diff-driven (sha256 vs content_hash), index second-brain repo

### P3
- [ ] bge-reranker-v2-m3 rerank top-50→8, env flag, eval A/B
- [ ] Embed batch 64 + query cache

Last updated: 2026-09-06
