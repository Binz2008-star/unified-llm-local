/**
 * Code It - Intelligence Console / ROBEN AI OS Dashboard
 * Phase 3 - Token-Budget Tracking
 *
 * Author: Second Brain KB Team
 * License: MIT
 */

export interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

export interface Budget {
  window: number;
  used: number;
  remaining: number;
}

export interface CompressionMeta {
  tokensUsed: number;
  compressionRatio: number;
  historyTruncated: number;
}

export const MODEL_WINDOW = 200_000;
export const OUTPUT_RESERVE_RATIO = 0.15;

const TOKENS_PER_CHAR = 4; // ~4 chars per token (cl100k_base heuristic)

export function estimateTokens(messages: Message[]): number {
  const textLength = messages.reduce((sum, m) => sum + m.content.length, 0);
  return Math.ceil(textLength / TOKENS_PER_CHAR);
}

export function usableBudget(window = MODEL_WINDOW): number {
  return Math.floor(window * (1 - OUTPUT_RESERVE_RATIO));
}

export function needsCompression(messages: Message[], budget: number): boolean {
  return estimateTokens(messages) > budget;
}

export function computeBudget(messages: Message[], window = MODEL_WINDOW): Budget {
  const used = estimateTokens(messages);
  const usable = usableBudget(window);
  return {
    window,
    used,
    remaining: Math.max(0, usable - used),
  };
}
