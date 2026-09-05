/**
 * Code It - Intelligence Console / ROBEN AI OS Dashboard
 * Phase 3 - History Compression
 *
 * Author: Second Brain KB Team
 * License: MIT
 */

import { estimateTokens, usableBudget } from './budget.ts';
import type { CompressionMeta, Message } from './budget.ts';

const KEEP_LAST_N_VERBATIM = 6;

export interface CompressResult {
  messages: Message[];
  meta: CompressionMeta;
}

function summarize(messages: Message[]): string {
  const joined = messages.map((m) => `${m.role}: ${m.content}`).join('\n');
  return `[Summarized earlier context] ${joined}`.slice(0, 4000);
}

export async function compressHistory(
  messages: Message[],
  budget: number,
): Promise<CompressResult> {
  const originalTokens = estimateTokens(messages);
  let current = [...messages];
  let historyTruncated = 0;

  while (estimateTokens(current) > budget && current.length > KEEP_LAST_N_VERBATIM) {
    const keepNewest = current.slice(-KEEP_LAST_N_VERBATIM);
    const oldPart = current.slice(0, -KEEP_LAST_N_VERBATIM);
    const summaryText = summarize(oldPart);

    current = [
      { role: 'system', content: summaryText },
      ...keepNewest,
    ];
    historyTruncated += oldPart.length;
  }

  const finalTokens = estimateTokens(current);
  const target = usableBudget();

  return {
    messages: current,
    meta: {
      tokensUsed: finalTokens,
      compressionRatio: originalTokens > 0 ? finalTokens / originalTokens : 1,
      historyTruncated,
    },
  };
}
