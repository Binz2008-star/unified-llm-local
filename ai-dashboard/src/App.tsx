/**
 * Code It - Intelligence Console / ROBEN AI OS Dashboard
 * App.tsx - Main Layout Orchestrator with Active Reasoning Engine
 *
 * Author: Second Brain KB Team
 * License: MIT
 */

import React, { useCallback, useEffect, useMemo, useState } from "react";
import Header from "./components/Header";
import Sidebar from "./components/Sidebar";
import CodeReviewView from "./components/CodeReviewView";
import { SearchWidget } from "./components/SearchWidget";
import { MemoryExplorer } from "./components/MemoryExplorer";
import { WatcherStatus } from "./components/WatcherStatus";
import { AppProvider, useApp } from "./context/AppContext";
import { Notification, ReasoningMode } from "./types/index";

// ---------------------------------------------------------------------------
//  Workspace Views
// ---------------------------------------------------------------------------

function DashboardView() {
  const { telemetry, telemetryError, latencyHistory } = useApp();

  if (!telemetry) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-gray-500">
        <div className="animate-spin w-8 h-8 border-2 border-cyan-500/50 border-t-cyan-400 rounded-full mb-4" />
        <p className="text-sm font-mono">Connecting to telemetry…</p>
        {telemetryError && (
          <p className="text-xs text-red-400 mt-2">Backend not reachable at port :8000</p>
        )}
      </div>
    );
  }

  const cpuPct = telemetry.cpu?.totalPercent ?? 0;
  const memUsed = telemetry.memory?.usedBytes ?? 0;
  const memTotal = telemetry.memory?.totalBytes ?? 0;
  const usePct = telemetry.memory?.percent ?? 0;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4" dir="ltr">
      {/* System summary cards */}
      <MetricCard
        label="CPU Load"
        value={`${cpuPct.toFixed(1)}%`}
        sub={`${telemetry.cpu?.coreCount ?? 0} cores · ${telemetry.cpu?.cpuFreq ?? "—"}`}
        color={pctColor(cpuPct)}
      />
      <MetricCard
        label="Memory"
        value={`${usePct.toFixed(0)}%`}
        sub={`${fmtBytes(memUsed)} / ${fmtBytes(memTotal)}`}
        color={pctColor(usePct)}
      />
      <MetricCard
        label="Disk"
        value={`${(telemetry.disk?.usePct ?? 0).toFixed(0)}%`}
        sub={`${fmtBytes(telemetry.disk?.usedBytes ?? 0)} used`}
        color={pctColor(telemetry.disk?.usePct ?? 0)}
      />
      <MetricCard
        label="Uptime"
        value={fmtUptime(telemetry.uptime ?? 0)}
        sub={`${telemetry.procs ?? 0} processes`}
        color="#22d3ee"
      />

      {/* Recent latency history */}
      <div className="col-span-1 md:col-span-2 lg:col-span-4 bg-white/5 border border-white/10 rounded-xl p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-bold text-cyan-200 font-mono">LATENCY HISTORY</h3>
          <span className="text-[10px] text-gray-500 font-mono">Last {latencyHistory.length} runs</span>
        </div>
        {latencyHistory.length === 0 ? (
          <p className="text-xs text-gray-600 font-mono">
            No agent runs yet. Execute a command in the Agent Chat to populate telemetry.
          </p>
        ) : (
          <div className="space-y-2">
            {latencyHistory.slice(0, 8).map((rec) => (
              <div
                key={rec.id}
                className="flex items-center justify-between px-3 py-2 bg-black/30 rounded-lg border border-white/5"
              >
                <div className="flex items-center gap-3">
                  <span className="text-[10px] text-gray-500 font-mono">{rec.timeLabel}</span>
                  <span className="text-xs font-mono text-cyan-300">
                    {rec.totalLatencyMs.toFixed(0)}ms
                  </span>
                  <span
                    className="text-[9px] px-1.5 py-0.5 rounded-full"
                    style={{
                      color: rec.status === "success" ? "#22c55e" : rec.status === "warning" ? "#eab308" : "#ef4444",
                      backgroundColor: (rec.status === "success" ? "#22c55e" : rec.status === "warning" ? "#eab308" : "#ef4444") + "22",
                    }}
                  >
                    {rec.status.toUpperCase()}
                  </span>
                </div>
                <div className="text-[10px] text-gray-500 font-mono hidden sm:flex items-center gap-3">
                  <span>R:{rec.phaseTimings.researcherMs}ms</span>
                  <span>A:{rec.phaseTimings.architectMs}ms</span>
                  <span>E:{rec.phaseTimings.editorMs}ms</span>
                  <span>T:{rec.phaseTimings.testerMs}ms</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function MetricCard({ label, value, sub, color }: { label: string; value: string; sub: string; color: string }) {
  return (
    <div className="bg-white/5 border border-white/10 rounded-xl p-4 flex flex-col justify-between">
      <div className="flex items-center justify-between mb-2">
        <span className="text-[10px] uppercase tracking-widest text-gray-500 font-mono">{label}</span>
        <span className="w-2 h-2 rounded-full" style={{ backgroundColor: color, boxShadow: `0 0 8px ${color}` }} />
      </div>
      <div className="text-3xl font-bold font-mono" style={{ color }}>{value}</div>
      <div className="text-[11px] text-gray-500 font-mono mt-1 truncate">{sub}</div>
    </div>
  );
}

function pctColor(pct: number): string {
  if (pct < 50) return "#22c55e";
  if (pct < 80) return "#eab308";
  return "#ef4444";
}

function fmtBytes(bytes: number): string {
  if (!bytes || isNaN(bytes)) return "0 B";
  const u = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${u[i]}`;
}

function fmtUptime(secs: number): string {
  if (!secs) return "—";
  const d = Math.floor(secs / 86400);
  const h = Math.floor((secs % 86400) / 3600);
  const m = Math.floor((secs % 3600) / 60);
  if (d > 0) return `${d}d ${h}h`;
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

// ---------------------------------------------------------------------------
//  Agent Chat View (With Reasoning Mode Controls & Auto-Scroll)
// ---------------------------------------------------------------------------

function AgentChatView() {
  const { sendPrompt, isProcessing, reasoningMode, setReasoningMode } = useApp();
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<{ role: "user" | "assistant"; content: string; mode?: ReasoningMode }[]>([]);

  const scrollToBottom = useCallback(() => {
    const chatContainer = document.getElementById("chat-messages-container");
    if (chatContainer) {
      chatContainer.scrollTop = chatContainer.scrollHeight;
    }
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, isProcessing, scrollToBottom]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isProcessing) return;
    const content = input.trim();
    setInput("");

    setMessages((m) => [...m, { role: "user", content, mode: reasoningMode }]);
    const reply = await sendPrompt(content);
    if (reply) {
      setMessages((m) => [...m, { role: "assistant", content: reply, mode: reasoningMode }]);
    } else {
      setMessages((m) => [...m, { role: "assistant", content: `⚠️ Backend unreachable. Is the FastAPI server running on :8000?` }]);
    }
  };

  const modes: { id: ReasoningMode; label: string; desc: string }[] = [
    { id: ReasoningMode.Fast, label: "⚡ Fast", desc: "Quick direct execution" },
    { id: ReasoningMode.DeepReasoning, label: "🧠 Deep Reasoning", desc: "Multi-step analytical reflection" },
    { id: ReasoningMode.Architect, label: "🏗️ Architect", desc: "System design & structured planning" },
  ];

  return (
    <div className="flex flex-col h-full" dir="ltr">
      {/* Reasoning Mode Switcher Bar */}
      <div className="flex items-center justify-between px-4 py-2.5 bg-black/40 border-b border-white/10 text-xs">
        <span className="text-gray-400 font-mono text-[11px]">REASONING MODE:</span>
        <div className="flex gap-1.5">
          {modes.map((m) => (
            <button
              key={m.id}
              type="button"
              onClick={() => setReasoningMode(m.id)}
              className={`px-2.5 py-1 rounded-lg font-mono text-[11px] transition-all ${reasoningMode === m.id
                  ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 font-semibold"
                  : "bg-white/5 text-gray-400 hover:bg-white/10 border border-transparent"
                }`}
              title={m.desc}
            >
              {m.label}
            </button>
          ))}
        </div>
      </div>

      {/* Messages Feed */}
      <div id="chat-messages-container" className="flex-1 overflow-y-auto space-y-3 p-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-gray-500 text-sm font-mono space-y-2">
            <span className="text-3xl">🧠</span>
            <p>Select a reasoning mode and enter a command...</p>
          </div>
        )}
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`max-w-[85%] px-4 py-3 rounded-xl text-sm font-mono whitespace-pre-wrap ${msg.role === "user"
                ? "ml-auto bg-cyan-500/20 border border-cyan-500/40 text-cyan-100"
                : "bg-white/5 border border-white/10 text-gray-200"
              }`}
          >
            {msg.mode && (
              <div className="text-[9px] uppercase tracking-wider text-cyan-400/70 mb-1 border-b border-cyan-500/10 pb-1">
                [{msg.mode.replace("_", " ")}]
              </div>
            )}
            {msg.content}
          </div>
        ))}
        {isProcessing && (
          <div className="flex items-center gap-2 text-cyan-400 text-xs font-mono bg-cyan-500/10 border border-cyan-500/20 p-3 rounded-xl">
            <span className="animate-spin w-3.5 h-3.5 border-2 border-cyan-500 border-t-transparent rounded-full" />
            Executing with [{reasoningMode}] active engine...
          </div>
        )}
      </div>

      {/* Input Bar */}
      <form onSubmit={handleSubmit} className="p-3 border-t border-white/10">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={`Ask in [${reasoningMode}] mode...`}
            disabled={isProcessing}
            className="flex-1 px-4 py-2.5 bg-[#0b1120] border border-white/15 rounded-xl text-sm text-white placeholder-gray-600 outline-none focus:border-cyan-500/50 transition-colors font-mono"
          />
          <button
            type="submit"
            disabled={isProcessing || !input.trim()}
            className="px-5 py-2.5 bg-gradient-to-r from-cyan-600 to-violet-600 hover:from-cyan-500 hover:to-violet-500 text-white rounded-xl text-sm font-semibold disabled:opacity-50 disabled:cursor-not-allowed transition-all font-mono"
          >
            Send
          </button>
        </div>
      </form>
    </div>
  );
}

// ---------------------------------------------------------------------------
//  Notifications Toast Container
// ---------------------------------------------------------------------------

function Notifications() {
  const { notifications, dismissNotification } = useApp();

  if (notifications.length === 0) return null;

  const styleFor = (t: Notification["type"]) => {
    switch (t) {
      case "success": return { border: "#22c55e", text: "#86efac", bg: "#22c55e22" };
      case "warning": return { border: "#eab308", text: "#fde047", bg: "#eab30822" };
      case "error": return { border: "#ef4444", text: "#fca5a5", bg: "#ef444422" };
      default: return { border: "#22d3ee", text: "#a5f3fc", bg: "#22d3ee22" };
    }
  };

  return (
    <div className="fixed top-16 right-4 z-50 space-y-2 w-80 max-w-[90vw]" dir="ltr">
      {notifications.map((n) => {
        const s = styleFor(n.type);
        return (
          <div
            key={n.id}
            className="rounded-xl shadow-2xl shadow-black/40 backdrop-blur-md border px-4 py-3 flex items-start gap-3 animate-slide-in-left"
            style={{ background: s.bg, borderColor: s.border }}
          >
            <div className="flex-1 min-w-0">
              <div className="text-sm font-bold" style={{ color: s.text }}>{n.title}</div>
              <div className="text-xs text-gray-300 font-mono mt-0.5 break-words">{n.message}</div>
            </div>
            <button
              type="button"
              onClick={() => dismissNotification(n.id)}
              className="text-gray-400 hover:text-white transition-colors text-xs"
              title="Dismiss"
            >
              ✕
            </button>
          </div>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
//  Workspace Content Switcher
// ---------------------------------------------------------------------------

function Workspace() {
  const { activeView } = useApp();

  const content = useMemo<Record<string, React.ReactNode>>(
    () => ({
      dashboard: <DashboardView />,
      chat: <AgentChatView />,
      review: <CodeReviewView />,
      memory: (
        <div className="space-y-6">
          <div className="flex justify-end">
            <WatcherStatus />
          </div>
          <SearchWidget />
          <MemoryExplorer />
        </div>
      ),
      projects: (
        <PlaceholderView
          title="PROJECTS"
          description="Manage your registered workspaces and active project."
        />
      ),
      settings: (
        <PlaceholderView
          title="SETTINGS"
          description="Configure reasoning mode, theming, language, and system options."
        />
      ),
    }),
    []
  );

  return (
    <main className="flex-1 overflow-auto p-4 md:p-6">
      {content[activeView] ?? (
        <PlaceholderView title="UNKNOWN VIEW" description="Select a view from the sidebar." />
      )}
    </main>
  );
}

function PlaceholderView({ title, description }: { title: string; description: string }) {
  return (
    <div className="flex flex-col items-center justify-center h-96 text-center">
      <div className="text-5xl mb-4">🧩</div>
      <h2 className="text-2xl font-bold text-cyan-200 font-mono mb-2">{title}</h2>
      <p className="text-sm text-gray-500 font-mono max-w-md">{description}</p>
      <span className="mt-6 text-[10px] px-3 py-1 rounded-full bg-white/5 border border-white/10 text-gray-600 font-mono">
        Phase 3 · Coming Soon
      </span>
    </div>
  );
}

// ---------------------------------------------------------------------------
//  Main Shell Component
// ---------------------------------------------------------------------------

function Shell() {
  const { sidebarOpen } = useApp();

  return (
    <div className="min-h-screen bg-[#0a0f1c] text-gray-200 flex flex-col">
      <Sidebar />
      <div
        className={`flex flex-col flex-1 min-h-screen transition-all duration-300 ${sidebarOpen ? "md:ml-64" : ""
          }`}
      >
        <Header />
        <Workspace />
      </div>
      <Notifications />
    </div>
  );
}

// ---------------------------------------------------------------------------
//  App Root
// ---------------------------------------------------------------------------

export default function App() {
  return (
    <AppProvider>
      <Shell />
    </AppProvider>
  );
}
