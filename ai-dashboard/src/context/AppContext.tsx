/**
 * Code It - Intelligence Console / ROBEN AI OS Dashboard
 * AppContext.tsx - React 19 Context Orchestration
 *
 * Author: Second Brain KB Team
 * License: MIT
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

import {
  CodeReviewInput,
  CodeReviewResult,
  EvolutionLesson,
  EvolutionTodo,
  LatencyRecord,
  Notification,
  ProjectInfo,
  ReasoningMode,
  SystemResponse,
} from "../types/index";

// ---------------------------------------------------------------------------
//  API Base URL
// ---------------------------------------------------------------------------

const API_BASE =
  import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8000";

// ---------------------------------------------------------------------------
//  Context Value Interface
// ---------------------------------------------------------------------------

export interface AppContextValue {
  /** Current reasoning mode (fast / advanced / security) */
  reasoningMode: ReasoningMode;
  setReasoningMode: (mode: ReasoningMode) => void;

  /** Active project registry */
  projects: Record<string, ProjectInfo>;
  activeProject: string;
  currentProject: ProjectInfo | null;
  switchProject: (projectId: string) => Promise<void>;
  registerProject: (
    name: string,
    tech: string,
    icon?: string
  ) => Promise<ProjectInfo | null>;

  /** Telemetry state */
  telemetry: SystemResponse | null;
  telemetryError: boolean;
  isPolling: boolean;
  startPolling: (intervalMs?: number) => void;
  stopPolling: () => void;

  /** Chat state */
  isProcessing: boolean;
  sendPrompt: (message: string) => Promise<string | null>;
  clearChat: () => void;

  /** Code review */
  reviewCode: (
    input: CodeReviewInput
  ) => Promise<CodeReviewResult | null>;

  /** Latency history */
  latencyHistory: LatencyRecord[];
  addLatencyRecord: (record: LatencyRecord) => void;

  /** Memory & evolution */
  lessons: EvolutionLesson[];
  refreshLessons: () => Promise<void>;

  /** Notifications */
  notifications: Notification[];
  addNotification: (
    notification: Omit<Notification, "timestamp">
  ) => void;
  pushNotification: (
    type: Notification["type"],
    title: string,
    message: string,
    autoDismiss?: boolean
  ) => void;
  dismissNotification: (id: string) => void;
  clearNotifications: () => void;

  /** UI state */
  sidebarOpen: boolean;
  setSidebarOpen: (open: boolean) => void;
  activeView: string;
  setActiveView: (view: string) => void;
}

// ---------------------------------------------------------------------------
//  Context Creation
// ---------------------------------------------------------------------------

const AppContext = createContext<AppContextValue | undefined>(undefined);

export function useApp(): AppContextValue {
  const ctx = useContext(AppContext);
  if (!ctx) {
    throw new Error("useApp() must be used within <AppProvider>");
  }
  return ctx;
}

// ---------------------------------------------------------------------------
//  Notification Helper
// ---------------------------------------------------------------------------

function makeNotification(
  type: Notification["type"],
  title: string,
  message: string,
  autoDismiss = true
): Notification {
  return {
    id: `notif-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
    type,
    title,
    message,
    timestamp: Date.now(),
    autoDismiss,
  };
}

// ---------------------------------------------------------------------------
//  App Provider Component
// ---------------------------------------------------------------------------

export function AppProvider({ children }: { children: ReactNode }) {
  // --- Core State ---
  const [reasoningMode, setReasoningMode] = useState<ReasoningMode>(
    ReasoningMode.DeepReasoning
  );

  // --- Projects ---
  const [projects, setProjects] = useState<Record<string, ProjectInfo>>({});
  const [activeProject, setActiveProject] = useState<string>("");
  const [currentProject, setCurrentProject] = useState<ProjectInfo | null>(
    null
  );

  // --- Telemetry ---
  const [telemetry, setTelemetry] = useState<SystemResponse | null>(null);
  const [telemetryError, setTelemetryError] = useState(false);
  const [isPolling, setIsPolling] = useState(false);
  const pollingTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // --- Chat ---
  const [isProcessing, setIsProcessing] = useState(false);

  // --- Latency History ---
  const [latencyHistory, setLatencyHistory] = useState<LatencyRecord[]>([]);

  // --- Lessons ---
  const [lessons, setLessons] = useState<EvolutionLesson[]>([]);

  // --- Notifications ---
  const [notifications, setNotifications] = useState<Notification[]>([]);

  // --- UI ---
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [activeView, setActiveView] = useState("dashboard");

  // --- Auto-dismiss notifications ---
  useEffect(() => {
    const timers: ReturnType<typeof setTimeout>[] = [];
    notifications.forEach((n) => {
      if (n.autoDismiss && n.type !== "error") {
        const t = setTimeout(() => {
          setNotifications((prev) =>
            prev.filter((item) => item.id !== n.id)
          );
        }, 5000);
        timers.push(t);
      }
    });
    return () => timers.forEach(clearTimeout);
  }, [notifications]);

  // --- Notification helpers ---
  const pushNotification = useCallback(
    (
      type: Notification["type"],
      title: string,
      message: string,
      autoDismiss = true
    ) => {
      setNotifications((prev) => [
        ...prev,
        makeNotification(type, title, message, autoDismiss),
      ]);
    },
    []
  );

  const addNotification = useCallback(
    (notification: Omit<Notification, "timestamp">) => {
      pushNotification(
        notification.type,
        notification.title,
        notification.message,
        notification.autoDismiss
      );
    },
    [pushNotification]
  );

  const dismissNotification = useCallback((id: string) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
  }, []);

  const clearNotifications = useCallback(() => {
    setNotifications([]);
  }, []);

  // --- Project helpers ---
  const refreshProjects = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/projects`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      const projectMap: Record<string, ProjectInfo> = {};
      data.projects.forEach((p: ProjectInfo) => {
        projectMap[p.id] = p;
      });

      setProjects(projectMap);
      setCurrentProject(projectMap[data.activeProject] ?? null);
      return data;
    } catch {
      pushNotification("warning", "Projects", "Failed to load project registry");
      return null;
    }
  }, [pushNotification]);

  const switchProject = useCallback(
    async (projectId: string) => {
      try {
        const res = await fetch(
          `${API_BASE}/projects/switch`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ projectId }),
          }
        );
        const data = await res.json();
        if (data.success) {
          setActiveProject(projectId);
          setCurrentProject(projects[projectId] ?? null);
          pushNotification("success", "Project Switched", data.message ?? `Now on: ${projectId}`);
        } else {
          pushNotification("error", "Switch Failed", data.message ?? "Unknown error");
        }
      } catch {
        pushNotification("error", "Switch Failed", "Backend request failed");
      }
    },
    [projects, pushNotification]
  );

  const registerProject = useCallback(
    async (name: string, tech: string, icon = "📁") => {
      try {
        const res = await fetch(
          `${API_BASE}/projects/register`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name, tech, icon }),
          }
        );
        const data = await res.json();
        if (data.success && data.project) {
          setProjects((prev) => ({
            ...prev,
            [data.project.id]: data.project,
          }));
          pushNotification("success", "Project Added", `${name} registered successfully`);
          return data.project;
        }
        return null;
      } catch {
        pushNotification("error", "Add Failed", "Could not register project");
        return null;
      }
    },
    [pushNotification]
  );

  // --- Telemetry polling ---
  const fetchTelemetry = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/status`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setTelemetry(data);
      setTelemetryError(false);
    } catch {
      setTelemetryError(true);
    }
  }, []);

  const startPolling = useCallback(
    (intervalMs = 5000) => {
      if (pollingTimerRef.current) return;
      void fetchTelemetry();
      pollingTimerRef.current = setInterval(() => {
        void fetchTelemetry();
      }, intervalMs);
      setIsPolling(true);
    },
    [fetchTelemetry]
  );

  const stopPolling = useCallback(() => {
    if (pollingTimerRef.current) {
      clearInterval(pollingTimerRef.current);
      pollingTimerRef.current = null;
    }
    setIsPolling(false);
  }, []);

  // Start polling on mount + fetch projects
  useEffect(() => {
    startPolling(5000);
    void refreshProjects();
    return () => stopPolling();
  }, [startPolling, stopPolling, refreshProjects]);

  // --- Chat ---
  const sendPrompt = useCallback(
    async (message: string): Promise<string | null> => {
      setIsProcessing(true);
      try {
        const res = await fetch(`${API_BASE}/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            messages: [{ role: "user", content: message }],
            reasoning_mode: reasoningMode,
            project_id: activeProject,
          }),
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        // Track latency
        const totalLatencyMs = data.latency_ms ?? 0;
        const record: LatencyRecord = {
          id: `lat-${Date.now()}`,
          timestamp: Date.now(),
          timeLabel: new Date().toLocaleTimeString(),
          totalLatencyMs,
          phaseTimings: {
            researcherMs: data.phases?.researcher_ms ?? 0,
            architectMs: data.phases?.architect_ms ?? 0,
            editorMs: data.phases?.editor_ms ?? 0,
            testerMs: data.phases?.tester_ms ?? 0,
            reviewMs: data.phases?.review_ms ?? 0,
          },
          tokensCount: data.tokens ?? 0,
          reasoningMode,
          projectId: activeProject,
          hasArtifact: Boolean(data.artifact),
          status: data.status ?? "success",
        };
        setLatencyHistory((prev) => [record, ...prev].slice(0, 50));

        if (data.artifact) {
          pushNotification("info", "Artifact Generated", "Analysis artifact is ready");
        }

        return data.reply ?? data.message ?? null;
      } catch {
        pushNotification("error", "Chat Error", "Request to backend failed");
        return null;
      } finally {
        setIsProcessing(false);
      }
    },
    [reasoningMode, activeProject, pushNotification]
  );

  const clearChat = useCallback(() => {
    // Placeholder - chat history managed by UI layer
  }, []);

  // --- Code review ---
  const reviewCode = useCallback(
    async (input: CodeReviewInput): Promise<CodeReviewResult | null> => {
      try {
        const res = await fetch(`${API_BASE}/research/review`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(input),
        });
        const data = await res.json();
        if (data.success) return data;
        return null;
      } catch {
        pushNotification("error", "Review Failed", "Could not analyze code");
        return null;
      }
    },
    [pushNotification]
  );

  // --- Lessons / Evolution ---
  const refreshLessons = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/memory`);
      const data = await res.json();
      if (data.todo && Array.isArray(data.todo)) {
        setLessons(
          data.todo.map((t: EvolutionTodo) => ({
            title: t.content,
            description: t.content,
            completed: t.completed,
            createdAt: "",
          }))
        );
      }
    } catch {
      // Silent - non-critical
    }
  }, []);

  useEffect(() => {
    void refreshLessons();
  }, [refreshLessons]);

  // --- Memoized value ---
  const value = useMemo<AppContextValue>(
    () => ({
      reasoningMode,
      setReasoningMode,

      projects,
      activeProject,
      currentProject,
      switchProject,
      registerProject,

      telemetry,
      telemetryError,
      isPolling,
      startPolling,
      stopPolling,

      isProcessing,
      sendPrompt,
      clearChat,

      reviewCode,

      latencyHistory,
      addLatencyRecord: (record: LatencyRecord) =>
        setLatencyHistory((prev) => [record, ...prev].slice(0, 50)),

      lessons,
      refreshLessons,

      notifications,
      addNotification,
      pushNotification,
      dismissNotification,
      clearNotifications,

      sidebarOpen,
      setSidebarOpen,
      activeView,
      setActiveView,
    }),
    [
      reasoningMode,
      projects,
      activeProject,
      currentProject,
      switchProject,
      registerProject,
      telemetry,
      telemetryError,
      isPolling,
      startPolling,
      stopPolling,
      isProcessing,
      sendPrompt,
      clearChat,
      reviewCode,
      latencyHistory,
      lessons,
      refreshLessons,
      notifications,
      addNotification,
      pushNotification,
      dismissNotification,
      clearNotifications,
      sidebarOpen,
      activeView,
    ]
  );

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export default AppContext;
