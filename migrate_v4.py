"""
Second Brain v4 - Phase 1 Schema & Data Migration
Idempotent: safe to re-run (ON CONFLICT DO NOTHING).

Usage:
  python migrate_v4.py            # create v4 tables + migrate chunks -> chunks_v4
  python migrate_v4.py --check    # verify schema + counts only
"""
import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import asyncpg

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "v4-extract" / "second-brain-v4"))
from chunker_v4 import V4_SCHEMA_SQL  # noqa: E402

load_dotenv(ROOT / ".env")

BATCH = 50


def emb_str(emb):
    if isinstance(emb, (list, tuple)):
        return "[" + ",".join(f"{x:.6f}" for x in emb) + "]"
    return str(emb).strip()


async def connect(dsn):
    return await asyncpg.connect(dsn, timeout=120, command_timeout=180)


def _istring(parts, marker):
    return [p for p in parts if marker in p]


async def run_schema(conn):
    print("=== Running v4 schema ===")
    # Skip the hybrid_search function (has dollar-quoted body that breaks naive split)
    parts = [s.strip() for s in V4_SCHEMA_SQL.split(";") if s.strip()]
    for stmt in parts:
        if "CREATE OR REPLACE FUNCTION" in stmt or "$$" in stmt:
            continue
        try:
            await conn.execute(stmt)
        except Exception as e:
            print(f"  WARN: {stmt[:50]}... -> {e}")
    print("  v4 tables + indexes + extensions OK")

    hybrid_sql = """CREATE OR REPLACE FUNCTION hybrid_search(
    query_text TEXT,
    query_embedding vector(768),
    match_count INT DEFAULT 10,
    rrf_k INT DEFAULT 60
) RETURNS TABLE (
    id INT,
    project_id TEXT,
    file_path TEXT,
    chunk_name TEXT,
    content TEXT,
    similarity FLOAT,
    rank FLOAT
) LANGUAGE plpgsql STABLE PARALLEL SAFE AS $$
DECLARE
    kw tsquery;
    candidate_k INT;
BEGIN
    kw := websearch_to_tsquery('english', query_text);
    IF kw IS NULL OR kw = ''::tsquery THEN
        kw := plainto_tsquery('english', query_text);
    END IF;

    candidate_k := GREATEST(match_count * 8, 50);

    RETURN QUERY
    WITH vec_cand AS (
        SELECT 
            v.id,
            (1 - (v.embedding <=> query_embedding))::FLOAT AS vec_sim,
            ROW_NUMBER() OVER (ORDER BY v.embedding <=> query_embedding) AS vec_rank
        FROM chunks_v4 v
        ORDER BY v.embedding <=> query_embedding
        LIMIT candidate_k
    ),
    kw_cand AS (
        SELECT 
            k.id,
            ROW_NUMBER() OVER (ORDER BY ts_rank_cd(k.content_tsv, kw) DESC) AS kw_rank
        FROM chunks_v4 k
        WHERE k.content_tsv @@ kw
        ORDER BY ts_rank_cd(k.content_tsv, kw) DESC
        LIMIT candidate_k
    ),
    combined AS (
        SELECT 
            COALESCE(v.id, k.id) AS cand_id,
            COALESCE(v.vec_sim, (1 - (c.embedding <=> query_embedding))::FLOAT) AS vec_sim,
            (
                COALESCE(1.0 / (rrf_k + v.vec_rank), 0.0) + 
                COALESCE(1.0 / (rrf_k + k.kw_rank), 0.0)
            )::FLOAT AS rrf_score
        FROM vec_cand v
        FULL OUTER JOIN kw_cand k ON v.id = k.id
        JOIN chunks_v4 c ON c.id = COALESCE(v.id, k.id)
    )
    SELECT
        c.id,
        c.project_id,
        c.file_path,
        c.chunk_name,
        c.content,
        cb.vec_sim AS similarity,
        cb.rrf_score AS rank
    FROM combined cb
    JOIN chunks_v4 c ON c.id = cb.cand_id
    ORDER BY cb.rrf_score DESC
    LIMIT match_count;
END; $$;"""
    await conn.execute(hybrid_sql)
    print("  hybrid_search() OK (RRF)")


async def populate_projects(conn):
    env_map = {
        "content-engine": os.getenv("PROJECT_CONTENT_ENGINE", ""),
        "lvyy": os.getenv("PROJECT_LVYY", ""),
        "rico": os.getenv("PROJECT_RICO", ""),
    }
    projects = await conn.fetch("SELECT DISTINCT project_id FROM chunks")
    n = 0
    for p in projects:
        pid = p["project_id"]
        path = env_map.get(pid, "")
        await conn.execute("""INSERT INTO projects (id, name, path)
            VALUES ($1,$2,$3) ON CONFLICT (id) DO NOTHING""", pid, pid, path)
        n += 1
    print(f"  projects synced: {n}")


async def migrate_chunks(conn):
    existing = await conn.fetchval("SELECT COUNT(*) FROM chunks_v4")
    chunks = await conn.fetch("""SELECT project_id, file_path, chunk_index, content,
        content_hash, language, start_line, end_line, embedding FROM chunks ORDER BY id""")
    rows = [(c["project_id"], c["file_path"], c["chunk_index"], c["content"],
             c["content_hash"], c["language"], c["start_line"], c["end_line"],
             emb_str(c["embedding"])) for c in chunks]
    print(f"  source chunks: {len(rows)} | chunks_v4 already: {existing}")

    i = 0
    while i < len(rows):
        batch = rows[i:i + BATCH]
        await conn.executemany("""
            INSERT INTO chunks_v4 (project_id, file_path, chunk_index, chunk_type,
                chunk_name, content, content_hash, language, start_line, end_line, embedding)
            VALUES ($1,$2,$3,'generic',NULL,$4,$5,$6,$7,$8,$9::vector)
            ON CONFLICT (project_id, file_path, chunk_index) DO NOTHING
        """, batch)
        i += BATCH
    cnt = await conn.fetchval("SELECT COUNT(*) FROM chunks_v4")
    print(f"  FINAL chunks_v4: {cnt}")


async def check(conn):
    v3 = await conn.fetchval("SELECT COUNT(*) FROM chunks")
    v4 = await conn.fetchval("SELECT COUNT(*) FROM chunks_v4")
    fn = await conn.fetchval("SELECT COUNT(*) FROM pg_proc WHERE proname='hybrid_search'")
    tsv = await conn.fetchval("SELECT COUNT(*) FROM chunks_v4 WHERE content_tsv IS NULL")
    proj = await conn.fetch("SELECT id FROM projects ORDER BY id")
    print(f"chunks(v3): {v3}")
    print(f"chunks_v4: {v4}")
    print(f"hybrid_search() exists: {bool(fn)}")
    print(f"rows with NULL content_tsv: {tsv}")
    print(f"projects: {[r['id'] for r in proj]}")
    ok = (v3 == v4 == 651 and fn == 1)
    print("MIGRATION OK" if ok else "MIGRATION INCOMPLETE")


async def main():
    dsn = os.environ["NEON_DSN"]
    conn = await connect(dsn)
    try:
        if "--check" in sys.argv:
            await check(conn)
            return
        await run_schema(conn)
        await populate_projects(conn)
        await migrate_chunks(conn)
        await check(conn)
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())