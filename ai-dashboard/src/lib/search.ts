/**
 * Phase 3.2 Semantic Search — memory lessons + hybrid RRF
 * Uses Ollama nomic-embed-text (768d) and Neon pgvector.
 * ESM, Node 22, strict types. Brute-force for memory (no HNSW), HNSW for chunks_v4.
 */

import pkg from 'pg';
const { Pool } = pkg;

const pool = new Pool({
  connectionString: process.env.NEON_DSN || process.env.DATABASE_URL,
});

const OLLAMA_EMBED_URL =
  process.env.OLLAMA_EMBED_URL || 'http://127.0.0.1:11434/api/embed';
const EMBED_MODEL = process.env.EMBED_MODEL || 'nomic-embed-text';

export interface SearchResult {
  id: number | string;
  lesson_id?: string;
  source_file?: string;
  content: string;
  tags?: string[];
  similarity?: number;
  rank?: number;
}

async function getEmbedding(text: string): Promise<number[]> {
  const res = await fetch(OLLAMA_EMBED_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ model: EMBED_MODEL, prompt: text }),
  });
  if (!res.ok) throw new Error(`Embed failed ${res.status}: ${await res.text().catch(() => res.statusText)}`);
  const data = (await res.json()) as { embedding?: number[]; embeddings?: number[][] };
  if (data.embedding) return data.embedding;
  if (data.embeddings?.[0]) return data.embeddings[0];
  throw new Error('Missing embedding');
}

// Exact brute-force cosine for memory (tiny table, no HNSW per schema_v4_memory.sql)
export async function searchMemory(query: string, topK = 5): Promise<SearchResult[]> {
  const emb = await getEmbedding(query);
  const vec = `[${emb.join(',')}]`;
  const client = await pool.connect();
  try {
    const r = await client.query(
      `SELECT id, lesson_id, source_file, content, tags,
              1 - (embedding <=> $1::vector) AS similarity
       FROM memory
       WHERE embedding IS NOT NULL
       ORDER BY embedding <=> $1::vector
       LIMIT $2`,
      [vec, topK]
    );
    return r.rows.map((row: any) => ({
      id: row.id,
      lesson_id: row.lesson_id,
      source_file: row.source_file,
      content: row.content,
      tags: row.tags,
      similarity: Number(row.similarity),
    }));
  } finally {
    client.release();
  }
}

// Hybrid RRF: vector (chunks_v4 HNSW) + keyword (chunks_v4 tsvector) + memory brute-force
// Simplified: if chunks_v4 not available, falls back to memory only
export async function hybridSearch(query: string, topK = 8): Promise<SearchResult[]> {
  const emb = await getEmbedding(query);
  const vec = `[${emb.join(',')}]`;
  const client = await pool.connect();
  try {
    // 1) Vector search over memory
    const mem = await client.query(
      `SELECT id, lesson_id, content, 'memory' as kind,
              1 - (embedding <=> $1::vector) AS score
       FROM memory WHERE embedding IS NOT NULL
       ORDER BY embedding <=> $1::vector LIMIT $2`,
      [vec, topK]
    );

    // 2) Vector search over chunks_v4 (HNSW) — may not exist on all envs, guard
    let chunks: any[] = [];
    try {
      const cr = await client.query(
        `SELECT id, content, 'chunk' as kind,
                1 - (embedding <=> $1::vector) AS score
         FROM chunks_v4 WHERE embedding IS NOT NULL
         ORDER BY embedding <=> $1::vector LIMIT $2`,
        [vec, topK]
      );
      chunks = cr.rows;
    } catch {
      // chunks_v4 missing — ignore
    }

    // 3) Keyword search over memory (ILIKE fallback for BM25)
    let kw: any[] = [];
    try {
      const kr = await client.query(
        `SELECT id, lesson_id, content, 'memory' as kind, 0.5 as score
         FROM memory WHERE content ILIKE '%' || $1 || '%' LIMIT $2`,
        [query.slice(0, 80), topK]
      );
      kw = kr.rows;
    } catch {
      // ignore
    }

    // RRF fusion k=60 (per README hybrid search)
    const k = 60;
    const fused = new Map<string, { item: any; rrf: number }>();
    const lists = [mem.rows, chunks, kw];
    for (const list of lists) {
      list.forEach((row: any, idx: number) => {
        const key = `${row.kind}:${row.id}:${row.lesson_id || ''}`;
        const prev = fused.get(key);
        const add = 1 / (k + idx + 1);
        if (prev) prev.rrf += add;
        else fused.set(key, { item: row, rrf: add });
      });
    }
    const sorted = [...fused.values()]
      .sort((a, b) => b.rrf - a.rrf)
      .slice(0, topK)
      .map(({ item, rrf }) => ({
        id: item.id,
        lesson_id: item.lesson_id,
        content: item.content,
        tags: item.tags,
        similarity: item.score,
        rank: rrf,
      }));
    return sorted;
  } finally {
    client.release();
  }
}
