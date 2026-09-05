export type ReasoningMode = 'fast' | 'advanced' | 'security';

export type Language = 'ar' | 'en';

export type SecondBrainProjectId = string;

export interface SecondBrainProject {
  id: string;
  name: string;
  description?: string;
  path: string;
  tech: string;
  icon?: string;
}

export type Project = SecondBrainProject;

export interface SystemTelemetry {
  cpu: number;
  cpu_cores: number[];
  cpu_freq: string | number;
  mem: {
    used: number; // bytes
    total: number; // bytes
    free: number;
    active: number;
  };
  disk: {
    used: number;
    total: number;
    free: number;
    usePct: number;
  };
  net: {
    in: number;
    out: number;
  };
  system: {
    host: string;
    os: string;
  };
  procs: number;
  uptime: number;
  neonConnected?: boolean;
  currentProject?: string;
}

export interface AttachedFile {
  name: string;
  size: number;
  type?: string;
  content?: string;
}

export interface CodeReviewSuggestion {
  id: string;
  type: 'performance' | 'security' | 'architecture';
  severity: 'critical' | 'warning' | 'info';
  title: string;
  description: string;
  suggestedFix?: string;
  lineRange?: string;
}

export interface CodeReviewResult {
  score: number; // 0-100
  grade: 'A+' | 'A' | 'B' | 'C' | 'D';
  summary: string;
  analyzedAt: number;
  performanceScore: number;
  securityScore: number;
  suggestions: CodeReviewSuggestion[];
  latencyMs?: number;
}

export interface CodeArtifact {
  title: string;
  language: string;
  code: string;
  description?: string;
  projectId?: string;
  review?: CodeReviewResult;
}

export interface ProcessingLatencyRecord {
  id: string;
  timestamp: number;
  timeLabel: string;
  querySummary: string;
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
  status: 'success' | 'warning' | 'error';
}

export interface AgentPhase {
  name: 'researcher' | 'architect' | 'editor' | 'tester' | 'memory';
  label: string;
  status: 'pending' | 'active' | 'completed';
  detail?: string;
}

export interface SystemAction {
  type:
    | 'create_project'
    | 'switch_project'
    | 'github_import'
    | 'change_mode'
    | 'open_settings'
    | 'open_telemetry'
    | 'export_markdown'
    | 'open_github'
    | 'open_latency_dashboard'
    | 'review_code';
  payload?: any;
  executedNotice?: string;
}

export interface AppSettings {
  language: Language;
  reasoningMode: ReasoningMode;
  explanationStyle: 'concise' | 'detailed';
  showQuickChips: boolean;
  zenMode: boolean;
  githubToken?: string;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
  projectId?: string;
  attachedFiles?: AttachedFile[];
  thinkingSteps?: string[];
  agentPhases?: AgentPhase[];
  isThinking?: boolean;
  activeStepIndex?: number;
  artifact?: CodeArtifact | null;
  modelSource?: string;
  telemetrySnapshot?: Partial<SystemTelemetry>;
  systemAction?: SystemAction;
  latencyRecord?: ProcessingLatencyRecord;
}

export interface Conversation {
  id: string;
  title: string;
  projectId?: string;
  createdAt: number;
  updatedAt: number;
  messages: Message[];
}
