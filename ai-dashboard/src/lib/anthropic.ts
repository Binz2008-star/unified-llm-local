/**
 * Code It - Intelligence Console
 * ROBEN AI OS Dashboard + Phase 3 - Anthropic streaming integration
 * Author: Second Brain KB Team
 * License: MIT
 */

import Anthropic from "@anthropic-ai/sdk";
import type { ChatChunk, Message, Route } from "../types/phase3";

let anthropicClient: Anthropic | null = null;

export function getAnthropicClient(): Anthropic {
  if (anthropicClient) return anthropicClient;
  anthropicClient = new Anthropic({
    apiKey: process.env.ANTHROPIC_API_KEY || "",
  });
  return anthropicClient;
}

export function hasAnthropicKey(): boolean {
  return !!(process.env.ANTHROPIC_API_KEY && process.env.ANTHROPIC_API_KEY.trim());
}

export interface StreamChatOptions {
  messages: Message[];
  model: string;
  maxTokens: number;
  system?: string;
  route: Route;
  signal?: AbortSignal;
}

export type StreamEvent =
  | { type: "route"; data: { route: Route; model: string } }
  | { type: "budget"; data: unknown }
  | { type: "token"; data: { delta: string } }
  | {
      type: "done";
      data: { usage: { inputTokens: number; outputTokens: number }; route: Route; model: string };
    }
  | { type: "error"; data: { message: string } };

export async function* streamChat(opts: StreamChatOptions): AsyncGenerator<ChatChunk> {
  if (!hasAnthropicKey()) {
    yield { type: "error", data: { message: "ANTHROPIC_API_KEY is not configured" } };
    return;
  }

  const client = getAnthropicClient();

  yield { type: "route", data: { route: opts.route, model: opts.model } };

  const anthropicMessages = opts.messages
    .filter((m) => m.role !== "system")
    .map((m) => ({
      role: m.role === "assistant" ? ("assistant" as const) : ("user" as const),
      content: m.content,
    }));

  const stream = client.messages.stream(
    {
      model: opts.model,
      max_tokens: opts.maxTokens,
      system: opts.system,
      messages: anthropicMessages,
      stream: true,
    },
    { signal: opts.signal }
  );

  for await (const event of stream) {
    if (event.type === "content_block_delta" && event.delta.type === "text_delta") {
      yield { type: "token", data: { delta: event.delta.text } };
    }
  }

  const final = await stream.finalMessage();
  yield {
    type: "done",
    data: {
      usage: {
        inputTokens: final.usage?.input_tokens ?? 0,
        outputTokens: final.usage?.output_tokens ?? 0,
      },
      route: opts.route,
      model: opts.model,
    },
  };
}
