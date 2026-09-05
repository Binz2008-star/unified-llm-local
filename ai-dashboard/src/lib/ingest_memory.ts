/**
 * Code It - Intelligence Console / ROBEN AI OS
 * Phase 3.2 - Memory Ingestion Pipeline
 * Parses memory/LESSONS.md, embeds via Ollama nomic-embed-text, upserts into Postgres (pgvector).
 * ESM, Node 22, strict types. Aligns with X:\second-brain-kb\.env:5 OLLAMA_EMBED_URL and database/schema_v4_memory.sql:1
 */

import fs from 'fs/promises';
import path from 'path';
import pkg from 'pg';
const { Pool } = pkg;
import { chunkMarkdown } from './chunkerMarkdown.js';

const pool = new Pool({
  connectionString: process.env.NEON_DSN || process.env.DATABASE_URL,
});

// X:\second-brain-kb\.env:5 uses /api/embed, blueprint used /api/embeddings — support both via env
const OLLAMA_EMBED_URL =
  process.env.OLLAMA_EMBED_URL || 'http://127.0.0.1:11434/api/embed';
const EMBED_MODEL = process.env.EMBED_MODEL || 'nomic-embed-text';

export async function getEmbedding(text: string): Promise<number[]> {
  const res = await fetch(OLLAMA_EMBED_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ model: EMBED_MODEL, prompt: text }),
  });
  if (!res.ok) {
    const errText = await res.text().catch(() => res.statusText);
    throw new Error(`Ollama embedding failed ${res.status}: ${errText}`);
  }
  const data = (await res.json()) as { embedding?: number[]; embeddings?: number[][] };
  // Ollama /api/embed returns { embeddings: [[...]] } for prompt, /api/embeddings returns { embedding: [...] }
  if (data.embedding) return data.embedding;
  if (data.embeddings?.[0]) return data.embeddings[0];
  throw new Error('Ollama response missing embedding');
}

export async function ingestLessonsFile(
  filePath = 'memory/LESSONS.md'
): Promise<number> {
  // Resolve from ai-dashboard/ or repo root: ai-dashboard/src/lib → ../../.. = X:\second-brain-kb
  const candidates = [
    path.resolve(process.cwd(), filePath),
    path.resolve(process.cwd(), '..', filePath),
    path.resolve('X:/second-brain-kb', filePath),
  ];
  let content: string | null = null;
  let resolvedPath = filePath;
  for (const p of candidates) {
    try {
      content = await fs.readFile(p, 'utf-8');
      resolvedPath = p;
      break;
    } catch {}
  }
  if (content === null) {
    throw new Error(`LESSONS.md not found tried ${candidates.join(', ')}`);
  }

  const chunks = chunkMarkdown(content, { source_file: filePath });
  console.log(`[Ingest] Parsed ${chunks.length} chunks from ${resolvedPath}`);

  const client = await pool.connect();
  try {
    for (const chunk of chunks) {
      const embedding = await getEmbedding(chunk.content);
      const vectorString = `[${embedding.join(',')}]`;
      await client.query(
        `INSERT INTO memory (lesson_id, source_file, content, embedding, tags, type, created_at)
         VALUES ($1, $2, $3, $4::vector, $5, 'lesson', NOW())
         ON CONFLICT (lesson_id) DO UPDATE SET
           content = EXCLUDED.content,
           embedding = EXCLUDED.embedding,
           tags = EXCLUDED.tags,
           source_file = EXCLUDED.source_file`,
        [chunk.lesson_id, chunk.source_file, chunk.content, vectorString, chunk.tags || []]
      );
      console.log(`[Ingest] Upserted ${chunk.lesson_id} (tokens: ${chunk.tokenCount})`);
    }
    // Optional: delete stale lessons no longer in file (keep exact sync)
    const currentIds = chunks.map((c) => c.lesson_id);
    if (currentIds.length) {
      await client.query(
        `DELETE FROM memory WHERE source_file = $1 AND lesson_id != ALL($2::text[]) AND type='lesson'`,
        [filePath, currentIds]
      );
    }
  } finally {
    client.release();
  }

  return chunks.length;
}

// CLI: tsx ai-dashboard/src/lib/ingest_memory.ts
if (import.meta.url === `file://${process.argv[1]?.replace(/\\/g, '/')}`) {
  ingestLessonsFile()
    .then((n) => {
      console.log(`[Ingest] Done: ${n} chunks`);
      process.exit(0);
    })
    .catch((e) => {
      console.error(e);
      process.exit(1);
    });
}
