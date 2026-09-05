# Golden Eval Set — Second Brain v4 (3)

**Purpose:** Regression gate for `search_brain` / `hybrid_search` quality. Run before/after any chunker, embed, or schema change.

## Files
- `golden.json` — 5 known-correct queries with expected `file_contains` + `project_id` + `min_rank` (default 3), one per indexed project:
  - `rico-gmail-oauth` → `src/services/gmail_oauth.py`
  - `rico-jotform-signature` → `src/rico_jotform_webhook.py`
  - `lvyy-domain` → `src/types/domain.ts`
  - `content-engine-youtube-auth` → `src/robin_content_engine/youtube_auth.py`
  - `content-engine-publishing` → `src/robin_content_engine/publishing.py`
- `run_golden.py` — runner: embeds via `nomic-embed-text`, searches via vector or `hybrid_search` RRF, computes Recall@1/3/8 and MRR.
- `reports/<mode>/summary.json` — aggregate of latest run.
- `reports/<mode>/scores.ndjson` — append-only per-question rows (hit rank, MRR, returned files, chunk counts) for drift tracking.

## Current baseline (2026-09-05, 9577 chunks: rico 7750, content-engine 1544, lvyy 283)
```
vector: 5/5 PASS  Recall@1 60%  Recall@3 100%  Recall@8 100%  MRR 0.800  (~5s)
```
Run captured in `eval/reports/vector/summary.json` + `scores.ndjson`.

## Usage
```bash
python eval/run_golden.py              # vector search (current search_brain)
python eval/run_golden.py --hybrid     # RRF hybrid
python eval/run_golden.py --json       # machine JSON output
python eval/run_golden.py --top-k 8    # search window (default 8)
```

## When to update
- Adding a golden: pick a question whose target file genuinely ranks top-3 today, else the gate fails for the wrong reason.
- If you change chunk size, embed model, or `hybrid_search` RRF_K, run eval and ensure Recall@3 stays 100% and MRR ≥0.8, else investigate.

## Integration
- CI gate candidate: fail if `passed < 5` or `recall@3 < 1.0`.
- When `second-brain` gets indexed, extend `golden.json` with queries targeting `mcp_server_v4.py`, `memory.py`, `brain_agent_v4.py`, `schema_v4.sql`.