/**
 * Phase 3.2 Markdown Chunker — heading-based, 512-token limit, 50-token overlap
 * Parses memory/LESSONS.md by `## ` headings, preserves Task/Plan/Solution blocks.
 * ESM, Node 22, strict types, aligned with Vite 6 + tsc --noEmit (ai-dashboard/package.json:12).
 */

export interface MemoryChunk {
  lesson_id: string;          // e.g. "2026-09-04-0108-rico" from heading
  source_file: string;        // default "memory/LESSONS.md"
  content: string;
  tokenCount: number;
  tags?: string[];
  metadata: {
    heading: string;
    project_id?: string;
    date?: string;
  };
}

const TOKEN_LIMIT = 512;
const OVERLAP = 50;

// Rough token estimate: ~4 chars per token (cl100k_base approx). For exact, use tiktoken.
function estimateTokens(text: string): number {
  return Math.ceil(text.length / 4);
}

function slugLessonId(heading: string): string {
  // heading: "## 2026-09-04 01:08 [lesson] rico" or "## 2026-09-04 [lesson] rico"
  // extract date+project
  const m = heading.match(/(\d{4}-\d{2}-\d{2})(?:\s+(\d{2}:\d{2}))?.*?(\w+)\s*$/);
  if (!m) return heading.replace(/^##\s+/, "").replace(/\W+/g, "-").slice(0, 48).toLowerCase();
  const date = m[1];
  const time = (m[2] || "0000").replace(":", "");
  const proj = m[3];
  return `${date}-${time}-${proj}`.toLowerCase();
}

function splitWithOverlap(text: string, limit: number, overlap: number): string[] {
  if (estimateTokens(text) <= limit) return [text];
  const paras = text.split(/\n\s*\n/);
  const chunks: string[] = [];
  let cur = "";
  for (const p of paras) {
    const candidate = cur ? `${cur}\n\n${p}` : p;
    if (estimateTokens(candidate) > limit && cur) {
      chunks.push(cur);
      // overlap: keep last `overlap` tokens worth of chars from cur
      const overlapChars = overlap * 4;
      const tail = cur.slice(-overlapChars);
      cur = `${tail}\n\n${p}`.trim();
      // if single para exceeds limit, hard split by chars
      if (estimateTokens(cur) > limit) {
        const hard = cur.match(/.{1,2000}/gs) || [cur];
        chunks.push(...hard.slice(0, -1));
        cur = hard[hard.length - 1];
      }
    } else {
      cur = candidate;
    }
  }
  if (cur) chunks.push(cur);
  return chunks;
}

export function chunkMarkdown(
  markdown: string,
  opts: { source_file?: string } = {}
): MemoryChunk[] {
  const source_file = opts.source_file ?? "memory/LESSONS.md";
  const sections = markdown.split(/^##\s+/m).filter(Boolean);
  // First section before any ## is intro — treat as one chunk if non-empty
  const chunks: MemoryChunk[] = [];

  for (const sec of sections) {
    const lines = sec.split("\n");
    const headingRaw = lines[0]?.trim() ?? "";
    const heading = `## ${headingRaw}`;
    const body = lines.slice(1).join("\n").trim();
    if (!body) continue;

    const lesson_id = slugLessonId(heading);
    const projectMatch = heading.match(/\b(rico|lvyy|second-brain|content-engine)\b/i);
    const dateMatch = heading.match(/(\d{4}-\d{2}-\d{2})/);

    // Preserve Task/Plan/Result as semantic unit: keep body together if under limit, else split with overlap
    const parts = splitWithOverlap(body, TOKEN_LIMIT, OVERLAP);
    for (let i = 0; i < parts.length; i++) {
      const content = parts.length === 1 ? `${heading}\n\n${body}`.trim() : `${heading} (part ${i + 1}/${parts.length})\n\n${parts[i]}`.trim();
      chunks.push({
        lesson_id: parts.length === 1 ? lesson_id : `${lesson_id}-p${i + 1}`,
        source_file,
        content,
        tokenCount: estimateTokens(content),
        tags: [],
        metadata: {
          heading: headingRaw,
          project_id: projectMatch?.[1]?.toLowerCase(),
          date: dateMatch?.[1],
        },
      });
    }
  }

  return chunks;
}

// Keep compatible with Python chunker_v4.py markdown mode for LESSONS.md
export const MEMORY_CHUNKER_CONFIG = {
  tokenLimit: TOKEN_LIMIT,
  overlap: OVERLAP,
  sourceFile: "memory/LESSONS.md",
} as const;
