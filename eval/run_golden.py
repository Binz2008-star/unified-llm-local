#!/usr/bin/env python3
"""
Golden Eval Runner — Second Brain v4 (3) Golden Eval Set

Evaluates search_brain (vector) and hybrid_search (RRF) against golden.json.
Metrics: Recall@1, @3, @8, MRR. Use as regression gate before/after index changes.

Usage:
  python eval/run_golden.py              # vector search (current)
  python eval/run_golden.py --hybrid     # hybrid RRF (if DB function exists)
  python eval/run_golden.py --top-k 8    # custom k
  python eval/run_golden.py --json       # machine JSON output

Golden format: each entry has id, query, expected {project_id?, file_contains, chunk_contains?}, min_rank
Pass = expected file appears in top min_rank (default 3) and contains chunk substring if specified.

Reports (per mode) written to eval/reports/<mode>/:
  scores.ndjson   — one row per question per run (append)
  summary.json    — aggregate over the latest run
"""

import argparse
import asyncio
import json
import os
import sys
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

import aiohttp
import asyncpg

OLLAMA_EMBED_URL = os.getenv("OLLAMA_EMBED_URL", "http://127.0.0.1:11434/api/embed")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
NEON_DSN = os.getenv("NEON_DSN")
GOLDEN_PATH = ROOT / "eval" / "golden.json"
REPORTS_DIR = ROOT / "eval" / "reports"


async def embed(text: str):
    async with aiohttp.ClientSession() as s:
        for _ in range(3):
            try:
                async with s.post(
                    OLLAMA_EMBED_URL, json={"model": EMBED_MODEL, "input": text}
                ) as r:
                    data = await r.json()
                    # nomic-embed-text returns {"embeddings": [[...]]} or {"embedding": [...]}
                    if "embeddings" in data:
                        return data["embeddings"][0]
                    if "embedding" in data:
                        return data["embedding"]
                    # fallback
                    return data["data"][0]["embedding"]
            except Exception:
                await asyncio.sleep(1)
    raise RuntimeError(f"embed failed for: {text[:60]}")


def matches(row, expected, query):
    """True if row matches expected file/project/chunk criteria."""
    fp = row.get("file_path") or ""
    pid = row.get("project_id") or ""
    content = row.get("content") or ""
    # file_contains: substring in file_path
    if expected.get("file_contains") and expected["file_contains"] not in fp:
        return False
    if expected.get("project_id") and expected["project_id"] != pid:
        return False
    # chunk_contains: substring in content (case-insensitive)
    cc = expected.get("chunk_contains")
    if cc and cc.lower() not in content.lower() and cc not in fp:
        # also allow match in chunk_name
        cn = row.get("chunk_name") or ""
        if cc not in cn:
            return False
    return True


async def search_vector(pool, query, embedding, top_k=8):
    emb_str = "[" + ",".join(f"{x:.6f}" for x in embedding) + "]"
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT project_id, file_path, chunk_name, content,
                      1 - (embedding <=> $1::vector) as similarity
               FROM chunks_v4
               ORDER BY embedding <=> $1::vector
               LIMIT $2""",
            emb_str,
            top_k,
        )
        return [dict(r) for r in rows]


async def search_hybrid(pool, query, embedding, top_k=8):
    emb_str = "[" + ",".join(f"{x:.6f}" for x in embedding) + "]"
    async with pool.acquire() as conn:
        try:
            rows = await conn.fetch(
                "SELECT * FROM hybrid_search($1, $2::vector, $3)", query, emb_str, top_k
            )
            # normalize: hybrid returns id, project_id, file_path, chunk_name, content, similarity, rank
            return [dict(r) for r in rows]
        except Exception as e:
            # fallback to vector if hybrid not present
            if "does not exist" in str(e) or "hybrid_search" in str(e):
                return await search_vector(pool, query, embedding, top_k)
            raise


async def evaluate(use_hybrid=False, top_k=8, verbose=True):
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    pool = await asyncpg.create_pool(NEON_DSN, min_size=1, max_size=2)
    results = []
    mrr_sum = 0
    recall_at = {1: 0, 3: 0, 8: 0}
    start = time.time()
    for item in golden:
        q = item["query"]
        exp = item["expected"]
        min_rank = item.get("min_rank", 3)
        emb = await embed(q)
        rows = await (
            search_hybrid(pool, q, emb, top_k) if use_hybrid else search_vector(pool, q, emb, top_k)
        )
        # find rank of first match
        rank = None
        for idx, r in enumerate(rows, start=1):
            if matches(r, exp, q):
                rank = idx
                break
        passed = rank is not None and rank <= min_rank
        mrr = 1.0 / rank if rank else 0
        mrr_sum += mrr
        for k in recall_at:
            if rank and rank <= k:
                recall_at[k] += 1
        results.append(
            {
                "id": item["id"],
                "query": q,
                "expected": exp,
                "rank": rank,
                "mrr": mrr,
                "passed": passed,
                "top_files": [f"{r['project_id']}/{r['file_path']}" for r in rows[:3]],
                "min_rank": min_rank,
                "search_top_k": top_k,
            }
        )
        if verbose:
            status = "PASS" if passed else "FAIL"
            rank_str = str(rank) if rank else "miss"
            print(
                f"[{status}] {item['id']:18} rank={rank_str:4} mrr={mrr:.3f} q={q[:50]:50} top={results[-1]['top_files'][0] if results[-1]['top_files'] else '—'}"
            )
            if not passed:
                print(
                    f"       expected file_contains={exp.get('file_contains')} chunk_contains={exp.get('chunk_contains')} project={exp.get('project_id', '*')}"
                )
                for i, r in enumerate(rows[:3], 1):
                    print(
                        f"       {i}. {r['project_id']}/{r['file_path']} :: {r.get('chunk_name') or ''} sim={r.get('similarity', r.get('rank', 0)):.3f}"
                    )

    chunk_count = {
        r["project_id"]: r["n"]
        for r in await pool.fetch(
            "SELECT project_id, COUNT(*) AS n FROM chunks_v4 GROUP BY project_id ORDER BY project_id"
        )
    }

    await pool.close()
    n = len(golden)
    elapsed = time.time() - start
    summary = {
        "mode": "hybrid" if use_hybrid else "vector",
        "run_id": uuid.uuid4().hex[:12],
        "n": n,
        "passed": sum(1 for r in results if r["passed"]),
        "recall@1": recall_at[1] / n,
        "recall@3": recall_at[3] / n,
        "recall@8": recall_at[8] / n,
        "mrr": mrr_sum / n,
        "elapsed_s": round(elapsed, 1),
    }
    _persist(summary, results, chunk_count)
    if verbose:
        print("\n" + "=" * 70)
        print(f"Golden Eval — {summary['mode']} — {n} queries — {elapsed:.1f}s")
        print(
            f"Passed: {summary['passed']}/{n}  Recall@1 {summary['recall@1']:.2%}  Recall@3 {summary['recall@3']:.2%}  Recall@8 {summary['recall@8']:.2%}  MRR {summary['mrr']:.3f}"
        )
        print("=" * 70)
        if summary["passed"] < n:
            fails = [r["id"] for r in results if not r["passed"]]
            print(f"Fails: {', '.join(fails)}")
    return summary, results


def _persist(summary, results, chunk_count):
    """Append one `scores.ndjson` row per question and rewrite `summary.json`."""
    mode_dir = REPORTS_DIR / summary["mode"]
    mode_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).isoformat()
    with open(mode_dir / "scores.ndjson", "a", encoding="utf-8") as fh:
        for r in results:
            fh.write(
                json.dumps(
                    {
                        "run_id": summary["run_id"],
                        "run_at": stamp,
                        "mode": summary["mode"],
                        "embed_model": EMBED_MODEL,
                        "top_k": r.get("search_top_k"),
                        "question_id": r["id"],
                        "query": r["query"],
                        "rank": r["rank"],
                        "mrr": r["mrr"],
                        "passed": r["passed"],
                        "chunk_count": chunk_count,
                        "expected": r["expected"],
                        "top_files": r["top_files"],
                    }
                )
                + "\n"
            )
    (mode_dir / "summary.json").write_text(
        json.dumps(
            {
                **summary,
                "run_at": stamp,
                "embed_model": EMBED_MODEL,
                "golden": [r["id"] for r in results],
                "chunk_count": chunk_count,
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hybrid", action="store_true", help="use hybrid_search RRF")
    ap.add_argument("--top-k", type=int, default=8)
    ap.add_argument("--json", action="store_true", help="output JSON only")
    args = ap.parse_args()
    summary, results = asyncio.run(
        evaluate(use_hybrid=args.hybrid, top_k=args.top_k, verbose=not args.json)
    )
    if args.json:
        print(json.dumps({"summary": summary, "results": results}, indent=2))


if __name__ == "__main__":
    main()
