# Phase 3 — Step 3.1: Intelligent Prompt Routing & Context Management

**Branch:** `feat/phase-3-intelligence` | **Base:** `main` @ `bd00eb8` | **Stack:** Node 22 + TypeScript ESM, Anthropic SDK (streaming), Vite 6 + React 19

## 1. Goals

### G1 — Intelligent Prompt Routing Middleware
Direct queries by complexity before hitting Anthropic:
- **Fast path:** simple Q&A, keyword search, low reasoning (haiku/fast model, `max_tokens` ~1k, temperature low).
- **Deep Reasoning:** multi-step analysis, chain-of-thought, codebase synthesis (sonnet/opus, extended thinking, higher budget).
- **Architect mode:** planning / critique / trade-off analysis (opus, structured output, tool-use).

Router input: `{ prompt, history, frontendMode, heuristics }` → output: `{ route, model, budget, systemPrompt, tools }`.

Heuristics: prompt length, keyword signals (`plan`, `architect`, `review`), history depth, explicit frontend toggle (`ai-dashboard/src/components/*` controls), token estimate via `tiktoken`/`anthropic` count.

### G2 — Token-Budget Tracking & History Compression
Prevent context window saturation:
- **Budget:** per-request `inputTokens + historyTokens + systemTokens ≤ modelWindow * 0.85` (reserve for output). Track against Anthropic limits (e.g. 200k).
- **History compression:** sliding window + summarization. Keep last N turns verbatim (e.g. 6), summarize older turns via fast model (`summarize(history[0:-N]) → summary`), inject as `system` or first `user` block.
- **Pre-flight check:** before `anthropic.messages.create`, run `countTokens(history+prompt)`; if over budget, compress iteratively until under. Emit `compressionMeta` for frontend telemetry.
- **Telemetry:** expose `tokensUsed`, `compressionRatio`, `historyTruncated` via API/stream.

### G3 — Clean API Endpoints / Types for React 19 Console
Map 1:1 to `ai-dashboard/src/components/*` controls (`Header.tsx`, `Sidebar.tsx`, `CodeReviewView.tsx`, `ChatInput.tsx`):
```
POST /api/phase3/route       → { route, model, budget }  (dry-run, no LLM)
POST /api/phase3/chat        → SSE stream ( Anthropic structured streaming )
POST /api/phase3/chat/stream → alias, top-level await, strict SSE
GET  /api/phase3/budget      → { window, used, remaining, compression }
```
Shared types in `ai-dashboard/src/types/phase3.ts` and `ai-dashboard/src/utils/phase3.ts` + backend `src/types.ts` (mirrored, Vite 6 ESM).

## 2. Tech Stack Constraints

- **Backend Runtime:** Node.js 22 LTS, TypeScript `module: nodenext`, `target: es2022`, ESM only, top-level `await` allowed. Entry `ai-dashboard/server.ts` (`tsx` dev, `esbuild` prod → `dist/server.js` per `package.json:8-9`).
- **AI SDK:** `anthropic` npm (latest), `client.messages.stream()` with `with` top-level await. No `require`. Strict `stream` handling, abort via `AbortController`.
- **Validation:** `zod` (or strict interfaces) for `RouteRequest`/`ChatRequest`. `tsc --noEmit` must pass (`package.json:12` `lint`). Align with `Vite v6.4.3` + `react@19.0.1`.

## 3. Architecture

```
React 19 (ChatInput/Sidebar mode toggle)
  ↓ POST /api/phase3/chat { prompt, mode, history, budgetHint }
Express (server.ts) → routingMiddleware → budgetManager → anthropicClient.stream()
  ↓ SSE: { event: 'route', data: { route } } → { event: 'token', data: { delta } } → { event: 'done', data: { usage } }
Frontend (ArtifactDrawer / MessageList) consumes stream
```

### 3.1 Routing Middleware (`src/middleware/routing.ts`)
```ts
export type Route = 'fast' | 'deep' | 'architect';
export interface RouteDecision { route: Route; model: string; maxTokens: number; systemPrompt: string; }
export async function decideRoute(input: { prompt: string; mode?: Route; historyLength: number; tokenEstimate: number }): Promise<RouteDecision>
```
- Priority: explicit `mode` from frontend (if user selects) > heuristics. Log decision to `X-Route` header.

### 3.2 Budget & Compression (`src/lib/budget.ts`, `src/lib/compress.ts`)
```ts
export function estimateTokens(messages: Message[]): number
export function needsCompression(messages: Message[], budget: number): boolean
export async function compressHistory(messages: Message[], budget: number): Promise<{ messages: Message[]; meta: CompressionMeta }>
```
- `estimateTokens` via `anthropic` token count or tiktoken `cl100k_base`. 
- `compressHistory` loops: slice oldest 50%, call fast summarizer, prepend summary as system message.

### 3.3 Anthropic Integration (`src/lib/anthropic.ts`)
- Singleton `new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY })`.
- `streamChat({ messages, model, maxTokens, system }): AsyncIterable<StreamChunk>` using `client.messages.stream({ model, messages, max_tokens, system, stream: true })`.
- Map to SSE: `res.write('event: token\ndata: JSON\n\n')`.

### 3.4 Types (`src/types.ts` ↔ `ai-dashboard/src/types/phase3.ts`)
```ts
export interface ChatRequest { prompt: string; history: Message[]; mode?: Route; budgetHint?: number }
export interface ChatChunk { type: 'route'|'token'|'budget'|'done'; data: unknown }
export interface Message { role: 'user'|'assistant'|'system'; content: string }
```

## 4. API Contract

### POST /api/phase3/route (dry-run)
Req: `ChatRequest` without streaming. Res: `RouteDecision & { tokenEstimate, wouldCompress }`.

### POST /api/phase3/chat (SSE)
Req: `ChatRequest`. Res: `text/event-stream`.
Events: `route`, `budget`, `token` (delta), `done` (`usage: { inputTokens, outputTokens }`), `error`.

Headers: `Content-Type: text/event-stream`, `Cache-Control: no-cache`, `X-Route`, `X-Compression`.

## 5. Frontend Mapping (React 19)

- `ChatInput.tsx` → add `mode` select (`fast`|`deep`|`architect`) + `budget` indicator.
- `Sidebar.tsx` → show `compressionMeta` badge.
- `MessageList.tsx` → render SSE `token` deltas incrementally (React 19 `use` / `Suspense` if streaming).
- `AppContext.tsx` → store `Route` + `budget` in context, persist in `localStorage`.

Strict interfaces: `Vite v6` HMR, `tsx` dev at `package.json:7`.

## 6. File Plan (on this branch)

```
ai-dashboard/
  server.ts                # wire /api/phase3/* routes
  src/
    middleware/routing.ts
    lib/budget.ts
    lib/compress.ts
    lib/anthropic.ts
    types/phase3.ts
  package.json             # add "anthropic", "zod" (npm install → lockfile)
docs/phase-3-step-3.1-spec.md  # this file
```

## 7. Verification

- `npm run lint` (`tsc --noEmit`) pass — strict types for `RouteDecision`, `ChatRequest`.
- `npm run build` → `vite build` + `esbuild server.ts --bundle` produces `dist/server.js` (`package.json:8`).
- Manual SSE: `curl -N -X POST http://localhost:3000/api/phase3/chat -H 'Content-Type: application/json' -d '{"prompt":"test","mode":"fast"}'`
- CI: `verify` job (`.github/workflows/ci.yml:28-34` lint + build) + Gitleaks + branch protection (`enforce_admins`, 1 review).
- Token budget: unit test `budget.test.ts` — case over-window triggers compression, under-window passes through.

## 8. Out of Scope (Next Steps)
- Step 3.2: persistent memory / RAG retrieval for history
- Step 3.3: cost metering & rate limiting per user

## 9. Commit Plan
1. `docs: add Phase 3 Step 3.1 spec (routing, budget, API)` — this file
2. `feat(phase3): add routing middleware + budget/compress lib`
3. `feat(phase3): add Anthropic streaming + /api/phase3/* routes + React 19 types`
