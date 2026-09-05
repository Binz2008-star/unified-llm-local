/**
 * Code It - Intelligence Console / ROBEN AI OS Dashboard
 * Type Definitions - Phase 2
 *
 * Author: Second Brain KB Team
 * License: MIT
 */

// ---------------------------------------------------------------------------
//  Core Telemetry Types
// ---------------------------------------------------------------------------

export interface CpuTelemetry {
  totalPercent: number;
  perCorePercent: number[];
  coreCount: number;
  cpuFreq: string;
}

export interface MemoryTelemetry {
  totalBytes: number;
  availableBytes: number;
  usedBytes: number;
  percent: number;
  activeBytes?: number;
}

export interface DiskTelemetry {
  totalBytes: number;
  usedBytes: number;
  freeBytes: number;
  usePct: number;
}

export interface NetTelemetry {
  in: number;
  out: number;
}

export interface SystemTelemetry {
  host: string;
  os: string;
}

export interface HostTelemetry {
  cpu: CpuTelemetry;
  memory: MemoryTelemetry;
  disk: DiskTelemetry;
  net: NetTelemetry;
  system: SystemTelemetry;
  uptime: number;
  procs: number;
  neonConnected: boolean;
}

// ---------------------------------------------------------------------------
//  Project Registry Types
// ---------------------------------------------------------------------------

export interface ProjectInfo {
  id: string;
  name: string;
  description: string;
  path: string;
  tech: string;
  icon: string;
}

export interface ProjectRegistry {
  projects: Record<string, ProjectInfo>;
  currentProject: string;
  activeProject: string;
}

// ---------------------------------------------------------------------------
//  Memory & Evolution Types
// ---------------------------------------------------------------------------

export interface MemoryLesson {
  id: string;
  type: "lesson" | "pattern" | "preference";
  content: string;
  projectId?: string;
  createdAt: string;
}

export interface MemoryFact {
  id: string;
  type: "fact" | "pattern" | "anti-pattern";
  content: string;
  projectId?: string;
  embedding?: number[];
  createdAt: string;
}

export interface EvolutionTodo {
  id: string;
  content: string;
  completed: boolean;
  projectId?: string;
}

export interface EvolutionLesson {
  title: string;
  description: string;
  completed: boolean;
  createdAt: string;
}

// ---------------------------------------------------------------------------
//  Code Review Types
// ---------------------------------------------------------------------------

export interface CodeReviewSuggestion {
  id: string;
  type: "performance" | "security" | "architecture";
  severity: "critical" | "warning" | "info";
  title: string;
  description: string;
  suggestedFix?: string;
  lineRange?: string;
}

export interface CodeReviewResult {
  score: number;
  grade: "A+" | "A" | "B" | "C" | "D";
  summary: string;
  analyzedAt: number;
  performanceScore: number;
  securityScore: number;
  suggestions: CodeReviewSuggestion[];
  latencyMs?: number;
}

export interface CodeReviewInput {
  code: string;
  language: "python" | "typescript" | "javascript" | "other";
  title: string;
  projectId: string;
  lang: "ar" | "en";
}

// ---------------------------------------------------------------------------
//  Application State Types
// ---------------------------------------------------------------------------

export enum ReasoningMode {
  Fast = "fast",
  DeepReasoning = "deep_reasoning",
  Architect = "architect",
}

export interface AppState {
  readonly reasoningMode: ReasoningMode;
  readonly activeProject: string;
  readonly projects: Record<string, ProjectInfo>;
  readonly latencyHistory: LatencyRecord[];
  readonly isProcessing: boolean;
  readonly showSidebar: boolean;
  readonly language: "ar" | "en";
  readonly notifications: Notification[];
}

export interface LatencyRecord {
  id: string;
  timestamp: number;
  timeLabel: string;
  totalLatencyMs: number;
  phaseTimings: {
    researcherMs: number;
    architectMs: number;
    editorMs: number;
    testerMs: number;
    reviewMs: number;
  };
  tokensCount: number;
  reasoningMode: ReasoningMode;
  projectId: string;
  hasArtifact: boolean;
  status: "success" | "warning" | "error";
}

export interface Notification {
  id: string;
  type: "info" | "success" | "warning" | "error";
  title: string;
  message: string;
  timestamp: number;
  autoDismiss?: boolean;
}

// ---------------------------------------------------------------------------
//  Frontend State Types
// ---------------------------------------------------------------------------

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: number;
  thinkingSteps?: string[];
  artifact?: CodeReviewResult;
}

export interface ArtifactDrawerState {
  open: boolean;
  title: string;
  language: "ar" | "en";
  code: string;
  description: string;
}

export interface SystemSettings {
  theme: "dark" | "light";
  language: "ar" | "en";
  autoPlay: boolean;
  particleEffect: boolean;
  notificationSound: boolean;
}

// ---------------------------------------------------------------------------
//  API Response Types (from server.ts)
// ---------------------------------------------------------------------------

export interface SystemResponse {
  status: "ok" | "error";
  host: string;
  currentProject: string;
  projects: Record<string, ProjectInfo>;
  cpu: CpuTelemetry;
  memory: MemoryTelemetry;
  disk: DiskTelemetry;
  neonConnected: boolean;
  uptime?: number;
  procs?: number;
}

export interface ProjectResponse {
  success: boolean;
  newProject?: ProjectInfo;
  projects: ProjectInfo[];
  activeProject: string;
}

export interface MemoryResponse {
  activeProject: string;
  lessons: string[];
  todo: EvolutionTodo[];
  lastEvolutionTime: string;
}

// ---------------------------------------------------------------------------
//  Utility Types
// ---------------------------------------------------------------------------

export type DeepPartial<T> = {
  [P in keyof T]?: DeepPartial<T[P]>;
};

export type OptionalKeys<T, K extends keyof T> = Pick<Partial<T>, K> & Omit<T, K>;

export type Diff<T, U> = T extends U ? never : U extends T ? never : [T, U];
