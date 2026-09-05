# Phase 3 — Step 3.2: Vector Memory & Knowledge Graph Ingestion

**Branch:** `feat/phase-3-memory` | **Base:** `main` @ `787eac9` | **Stack:** Node 22 + TypeScript ESM, Ollama `nomic-embed-text` (768d), Postgres `pgvector`, Vite 6 + React 19

## 1. Goal
Establish persistent memory ingestion and semantic vector search mapping for `memory/LESSONS.md` (and `PATTERNS.md`/`CONTEXT.md`) so past engineering decisions are searchable via `sb.py`/`api.py` and linked to code chunks.

## 2. Strategy
- **Heading-based Markdown chunking (`##`):** Split `memory/LESSONS.md` on `## ` headings, preserve `Task:`, `Plan:`, `Solution` blocks intact. Enforce 512-token limit per chunk with 50-token overlap (sliding window inside oversized sections) to keep `nomic-embed-text` context without truncation.
- **Local Ollama embeddings (`nomic-embed-text`):** `OLLAMA_EMBED_URL=http://127.0.0.1:11434/api/embed` (`X:\second-brain-kb\.env:5`), `EMBED_DIM=768` (`schema_v4.sql`). Embed each chunk, store as `vector(768)` with `::vector` cast for asyncpg string handling.
- **Exact brute-force cosine search via Postgres `vector`:** `memory` is tiny (dozens of lessons) → no HNSW (recall miss, per `TECHNICAL-ARCHITECTURE.md:280`). Use `SELECT ... ORDER BY embedding <=> $1::vector LIMIT $2` (exact). `chunks_v4` keeps HNSW (9511 rows).
- **Automated file-watching updates:** `memory.py:1` watchdog watches `memory/LESSONS.md`; on change, re-chunk changed sections, re-embed, upsert `memory` (by `lesson_id`), delete stale. Also `reindex_v4.py --memory` manual trigger.

## 3. Schema Extension (`database/schema_v4_memory.sql`)
- `memory` additions: `source_file` (default `memory/LESSONS.md`), `lesson_id` (e.g. `2026-09-04-0108-rico`), `tags` (`TEXT[]` e.g. `{'decision','fixes'}`), `linked_chunk_id` (FK to `chunks_v4.id` nullable, direct link for simple case).
- `memory_edges` for graph: `from_memory_id → to_chunk_id` with `relation ∈ ('implements','fixes','references')`, `created_at`. Allows lessons to reference multiple code chunks.

## 4. Markdown Chunker (`ai-dashboard/src/lib/chunkerMarkdown.ts` + Python `chunker_v4.py` markdown mode)
- Parse Markdown by `## `, extract `lesson_id` from heading (`## 2026-09-04 01:08 [lesson] rico`), capture `Task:`/`Plan:`/`Result:` blocks as single semantic unit if <512 tokens; else split on paragraph boundaries with 50-token overlap.
- Output: `{ id, lesson_id, source_file, content, tokenCount, tags, metadata: { heading, project_id } }`.
- Token count via `tiktoken` `cl100k_base` or `anthropic` count, aligned with `ai-dashboard/src/lib/budget.ts:1` estimator.

## 5. Ingestion Pipeline
```
memory/LESSONS.md → chunkerMarkdown.ts (heading split, 512/50) → Ollama embed (nomic-embed-text) → Postgres memory (INSERT ... ON CONFLICT (lesson_id) DO UPDATE) → memory_edges (link via code_graph search or manual tags)
```
- Upsert key: `lesson_id` unique. Delete where `source_file='memory/LESSONS.md'` and `lesson_id` not in current parse (stale removal).
- Search: `api.py:1` `/search` hybrid RRF (`chunks_v4` HNSW + `memory` brute-force) with `rrf_k=60`.

## 6. File Plan
```
docs/phase-3-step-3.2-spec.md
database/schema_v4_memory.sql
ai-dashboard/src/lib/chunkerMarkdown.ts  (ESM, Node 22, strict types)
chunker_v4.py  (add markdown mode, reuse token logic)
memory.py  (watchdog hook for LESSONS.md)
```

## 7. Verification
- `psql -f database/schema_v4_memory.sql` (idempotent `IF NOT EXISTS`) → `\d memory` shows new cols, `\d memory_edges` exists.
- `npm run lint` (`tsc --noEmit`) pass for `chunkerMarkdown.ts` types.
- `npm run build` (`vite build` + `esbuild server.ts`) pass.
- Manual: edit `memory/LESSONS.md`, run `python reindex_v4.py --memory`, `SELECT count(*) FROM memory; SELECT lesson_id FROM memory LIMIT 5;`
- `sb.py search "lesson"` returns `memory` chunks via brute-force.
- CI: `verify` (`.github/workflows/ci.yml:28-34`) + `Gitleaks` green, branch protection on `main` holds.

## 8. Out of Scope
- Step 3.3: GraphRAG traversal + reranking
- Step 3.4: Cost metering for embeddings

## 9. Commit Plan
1. `docs: add Phase 3 Step 3.2 spec (feat/phase-3-memory)` — this file
2. `feat(memory): add schema extension database/schema_v4_memory.sql`
3. `feat(memory): add Markdown chunker (heading, 512/50, lessons)`
