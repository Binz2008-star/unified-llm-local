/**
 * Code It - Intelligence Console / ROBEN AI OS Dashboard
 * Phase 3 - Intelligent Prompt Routing Middleware
 *
 * Author: Second Brain KB Team
 * License: MIT
 */

export type Route = 'fast' | 'deep' | 'architect';

export interface RouteDecision {
  route: Route;
  model: string;
  maxTokens: number;
  systemPrompt: string;
}

export interface RouteInput {
  prompt: string;
  mode?: Route;
  historyLength: number;
  tokenEstimate: number;
}

const MODEL_MAP: Record<Route, string> = {
  fast: 'claude-3-5-haiku-latest',
  deep: 'claude-sonnet-4-5',
  architect: 'claude-opus-4-1',
};

const BUDGET_MAP: Record<Route, number> = {
  fast: 1024,
  deep: 4096,
  architect: 8192,
};

const SYSTEM_PROMPT_MAP: Record<Route, string> = {
  fast: 'Answer concisely. Prefer short, direct answers to simple questions.',
  deep: 'Reason through multi-step analysis using chain-of-thought. Synthesize across code and context before answering.',
  architect: 'Act as a software architect. Produce structured plans, trade-off analyses, and critique. Prefer bullet points and clear sections.',
};

const FAST_KEYWORDS = ['what is', 'whats', 'who is', 'define', 'meaning', 'simple', 'short'];
const DEEP_KEYWORDS = ['why', 'explain', 'analyse', 'analyze', 'compare', 'synthesis', 'synthesize', 'codebase', 'depth'];
const ARCHITECT_KEYWORDS = ['plan', 'architecture', 'architect', 'design', 'trade-off', 'tradeoff', 'roadmap', 'strategy'];

const LONG_PROMPT_THRESHOLD = 240;
const LONG_TOKEN_THRESHOLD = 800;

function matchKeywords(prompt: string, keywords: string[]): boolean {
  const lower = prompt.toLowerCase();
  return keywords.some((kw) => lower.includes(kw));
}

function scoreRoute(prompt: string): Record<Route, number> {
  return {
    fast: matchKeywords(prompt, FAST_KEYWORDS) ? 1 : 0,
    deep: matchKeywords(prompt, DEEP_KEYWORDS) ? 1 : 0,
    architect: matchKeywords(prompt, ARCHITECT_KEYWORDS) ? 1 : 0,
  };
}

export async function decideRoute(input: RouteInput): Promise<RouteDecision> {
  let route: Route;

  if (input.mode && input.mode in MODEL_MAP) {
    route = input.mode;
  } else {
    const scores = scoreRoute(input.prompt);
    const lengthBoost = input.prompt.length > LONG_PROMPT_THRESHOLD ? 1 : 0;
    const tokenBoost = input.tokenEstimate > LONG_TOKEN_THRESHOLD ? 1 : 0;
    const historyBoost = input.historyLength > 6 ? 1 : 0;

    const total = {
      fast: scores.fast - historyBoost,
      deep: scores.deep + lengthBoost + tokenBoost + historyBoost,
      architect: scores.architect + (input.prompt.includes('plan') ? 1 : 0),
    };

    route = total.deep >= total.architect && total.deep > total.fast ? 'deep' : 'fast';
    if (total.architect > total.deep && total.architect >= total.fast) {
      route = 'architect';
    }
  }

  return {
    route,
    model: MODEL_MAP[route],
    maxTokens: BUDGET_MAP[route],
    systemPrompt: SYSTEM_PROMPT_MAP[route],
  };
}
