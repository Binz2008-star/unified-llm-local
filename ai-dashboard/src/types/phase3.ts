/**
 * Code It - Intelligence Console
 * ROBEN AI OS Dashboard + Phase 3 - Intelligent Prompt Routing & Context Management
 * Author: Second Brain KB Team
 * License: MIT
 */

export type Route = "fast" | "deep" | "architect";

export interface RouteDecision {
  route: Route;
  model: string;
  maxTokens: number;
  systemPrompt: string;
}

export interface Message {
  role: "user" | "assistant" | "system";
  content: string;
}

export interface ChatRequest {
  prompt: string;
  history?: Message[];
  mode?: Route;
  budgetHint?: number;
}

export type ChatChunkType = "route" | "budget" | "token" | "done" | "error";

export interface ChatChunk {
  type: ChatChunkType;
  data: unknown;
}

export interface CompressionMeta {
  tokensUsed: number;
  compressionRatio: number;
  historyTruncated: boolean;
  keptVerbatim: number;
  summarized: number;
}

export interface BudgetInfo {
  window: number;
  used: number;
  remaining: number;
  compression: CompressionMeta | null;
}

export interface ChatUsage {
  inputTokens: number;
  outputTokens: number;
}

export interface ChatDone {
  usage: ChatUsage;
  route: Route;
  model: string;
}
