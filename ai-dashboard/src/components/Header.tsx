/**
 * Code It - Intelligence Console / ROBEN AI OS Dashboard
 * Header.tsx - Console Header with Project Switcher, Telemetry, Latency
 *
 * Author: Second Brain KB Team
 * License: MIT
 */

import { useEffect, useMemo, useRef, useState } from "react";
import { useApp } from "../context/AppContext";
import { ReasoningMode } from "../types/index";

// ---------------------------------------------------------------------------
//  Utility: format bytes
// ---------------------------------------------------------------------------

function formatBytes(bytes: number): string {
  if (!bytes || isNaN(bytes)) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${units[i]}`;
}

// ---------------------------------------------------------------------------
//  Utility: format latency color
// ---------------------------------------------------------------------------

function latencyColor(ms: number): string {
  if (ms < 800) return "#22c55e";
  if (ms < 2000) return "#eab308";
  return "#ef4444";
}

// ---------------------------------------------------------------------------
//  Utility: icons
// ---------------------------------------------------------------------------

const ICONS = {
  cpu: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-3.5 h-3.5">
      <rect x="4" y="4" width="16" height="16" rx="2" />
      <rect x="9" y="9" width="6" height="6" />
      <path d="M9 2v2M15 2v2M9 20v2M15 20v2M2 9h2M2 15h2M20 9h2M20 15h2" />
    </svg>
  ),
  memory: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-3.5 h-3.5">
      <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
      <polyline points="3.27 6.96 12 12.01 20.73 6.96" />
      <line x1="12" y1="22.08" x2="12" y2="12" />
    </svg>
  ),
  network: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-3.5 h-3.5">
      <circle cx="12" cy="12" r="10" />
      <line x1="2" y1="12" x2="22" y2="12" />
      <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
    </svg>
  ),
  clock: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-3.5 h-3.5">
      <circle cx="12" cy="12" r="10" />
      <polyline points="12 6 12 12 16 14" />
    </svg>
  ),
  bolt: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-3.5 h-3.5">
      <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
    </svg>
  ),
  chevron: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-3.5 h-3.5">
      <polyline points="6 9 12 15 18 9" />
    </svg>
  ),
} as const;

// ---------------------------------------------------------------------------
//  Latency Pill Component
// ---------------------------------------------------------------------------

function LatencyPill({ label, value, ms }: { label: string; value: string; ms?: number }) {
  return (
    <div className="flex items-center gap-1.5 px-2 py-1 bg-white/5 border border-white/10 rounded-lg">
      <span className="text-[10px] uppercase tracking-wider text-cyan-400/70 font-mono">{label}</span>
      <span
        className="text-[11px] font-mono font-semibold"
        style={{ color: ms !== undefined ? latencyColor(ms) : "#22d3ee" }}
      >
        {value}
      </span>
    </div>
  );
}

// ---------------------------------------------------------------------------
//  Project Switcher Dropdown
// ---------------------------------------------------------------------------

function ProjectSwitcher() {
  const { projects, activeProject, switchProject } = useApp();
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  const current = projects[activeProject];

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  return (
    <div className="relative" ref={menuRef} dir="ltr">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-2 px-3 py-2 bg-gradient-to-r from-cyan-500/10 to-violet-500/10 border border-cyan-500/30 hover:border-cyan-400/60 rounded-xl text-sm text-cyan-100 transition-colors"
        aria-haspopup="listbox"
        aria-expanded={open}
        title="Switcher Project"
      >
        <span className="text-base">{current?.icon ?? "📁"}</span>
        <span className="max-w-40 truncate font-medium text-cyan-50">
          {current?.name ?? "No Project"}
        </span>
        <span className="opacity-60">{ICONS.chevron}</span>
      </button>

      {open && (
        <div
          className="absolute z-50 mt-2 w-64 max-h-72 overflow-auto bg-[#0b1120]/95 backdrop-blur-md border border-white/10 rounded-xl shadow-2xl shadow-black/50 py-1"
          role="listbox"
        >
          {Object.entries(projects).map(([id, proj]) => (
            <button
              key={id}
              type="button"
              onClick={() => {
                void switchProject(id);
                setOpen(false);
              }}
              className={`w-full flex items-center gap-2 px-3 py-2.5 text-left text-sm transition-colors ${id === activeProject
                ? "bg-cyan-500/15 text-cyan-200 border-l-2 border-cyan-400"
                : "text-gray-300 hover:bg-white/5"
                }`}
              role="option"
              aria-selected={id === activeProject}
            >
              <span className="text-base">{proj.icon}</span>
              <div className="flex-1 min-w-0">
                <div className="truncate font-medium">{proj.name}</div>
                <div className="text-[10px] text-gray-500 truncate">{proj.tech}</div>
              </div>
              {id === activeProject && (
                <span className="text-cyan-400">●</span>
              )}
            </button>
          ))}
          {Object.keys(projects).length === 0 && (
            <div className="px-4 py-3 text-xs text-gray-500">
              No projects registered yet
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
//  Reasoning Mode Selector
// ---------------------------------------------------------------------------

function ModeSelector() {
  const { reasoningMode, setReasoningMode } = useApp();
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  const modes: { value: ReasoningMode; label: string; desc: string; color: string }[] = [
    { value: ReasoningMode.Fast, label: "⚡ Fast", desc: "Immediate response", color: "#22c55e" },
    { value: ReasoningMode.DeepReasoning, label: "🧠 Deep Reasoning", desc: "Deep reasoning", color: "#22d3ee" },
    { value: ReasoningMode.Architect, label: "🏗️ Architect", desc: "Architecture focus", color: "#a78bfa" },
  ];

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const current = modes.find((m) => m.value === reasoningMode);

  return (
    <div className="relative" ref={menuRef} dir="ltr">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-2 px-3 py-2 bg-white/5 border border-white/10 rounded-xl text-xs font-mono"
        title="Reasoning Mode"
        aria-haspopup="listbox"
        aria-expanded={open}
      >
        <span>{current?.label ?? "Mode"}</span>
        {ICONS.chevron}
      </button>

      {open && (
        <div className="absolute z-50 right-0 mt-2 w-56 bg-[#0b1120]/95 backdrop-blur-md border border-white/10 rounded-xl shadow-2xl shadow-black/50 py-1">
          {modes.map((m) => (
            <button
              key={m.value}
              type="button"
              onClick={() => {
                setReasoningMode(m.value);
                setOpen(false);
              }}
              className={`w-full flex items-start gap-2 px-3 py-2.5 text-left text-sm transition-colors ${m.value === reasoningMode ? "bg-white/5" : "hover:bg-white/5"
                }`}
            >
              <span
                className="text-base"
                style={{ color: m.color }}
              >
                {m.label.split(" ")[0]}
              </span>
              <div className="flex-1">
                <div className="text-xs font-medium" style={{ color: m.color }}>
                  {m.label}
                </div>
                <div className="text-[10px] text-gray-500">{m.desc}</div>
              </div>
              {m.value === reasoningMode && <span className="text-cyan-400">✓</span>}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
//  Telemetry Heartbeat Pill
// ---------------------------------------------------------------------------

function TelemetryPill() {
  const { telemetry, telemetryError, isPolling } = useApp();

  const statusClass = telemetryError
    ? "bg-red-500/15 border-red-500/30 text-red-400"
    : telemetry
      ? "bg-emerald-500/15 border-emerald-500/30 text-emerald-400"
      : "bg-amber-500/15 border-amber-500/30 text-amber-400";

  const statusText = telemetryError
    ? "OFFLINE"
    : telemetry
      ? "ONLINE"
      : "STARTING...";

  const dotClass = telemetryError
    ? "bg-red-500"
    : telemetry
      ? "bg-emerald-500 animate-pulse"
      : "bg-amber-500 animate-pulse";

  return (
    <div className={`flex items-center gap-2 px-3 py-2 border rounded-xl text-xs font-mono ${statusClass}`}>
      <span className={`w-2 h-2 rounded-full ${dotClass}`} />
      <span className="font-semibold tracking-wider">{statusText}</span>
      <span className="text-[10px] opacity-60">
        {isPolling ? "●" : "○"}
      </span>
    </div>
  );
}

// ---------------------------------------------------------------------------
//  Header Main Component
// ---------------------------------------------------------------------------

export default function Header() {
  const { telemetry, telemetryError, latencyHistory } = useApp();

  // Current clock time (updates every 20s)
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 20_000);
    return () => clearInterval(t);
  }, []);

  const lastLatency = useMemo(
    () => (latencyHistory.length ? latencyHistory[0]?.totalLatencyMs : undefined),
    [latencyHistory]
  );

  const cpuPercent = telemetry?.cpu?.totalPercent ?? 0;
  const memoryUsed = telemetry?.memory?.usedBytes ?? 0;

  const clock = now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

  return (
    <header className="w-full bg-[#0a0f1c]/90 backdrop-blur border-b border-white/10 sticky top-0 z-40">
      <div className="flex items-center justify-between gap-4 px-4 py-2.5">
        {/* Left: brand + project switcher */}
        <div className="flex items-center gap-3 min-w-0" dir="ltr">
          <div className="flex items-center gap-2 text-cyan-50 shrink-0">
            <span className="text-lg">🧠</span>
            <span className="hidden sm:block font-bold tracking-wide text-sm bg-gradient-to-r from-cyan-400 to-violet-400 bg-clip-text text-transparent">
              ROBEN AI OS
            </span>
          </div>
          <ProjectSwitcher />
          <ModeSelector />
        </div>

        {/* Center: latency indicators */}
        <div className="hidden md:flex items-center gap-2" dir="ltr">
          <LatencyPill label="CPU" value={`${cpuPercent.toFixed(0)}%`} />
          <LatencyPill
            label="RAM"
            value={memoryUsed ? formatBytes(memoryUsed) : "--"}
          />
          <LatencyPill
            label="API"
            value={lastLatency !== undefined ? `${lastLatency.toFixed(0)}ms` : telemetryError ? "ERR" : "—"}
            ms={lastLatency}
          />
        </div>

        {/* Right: telemetry + clock */}
        <div className="flex items-center gap-3" dir="ltr">
          <TelemetryPill />
          <div className="flex items-center gap-1.5 text-xs font-mono text-gray-400">
            {ICONS.clock}
            <span>{clock}</span>
          </div>
        </div>
      </div>

      {/* Secondary strip: header context line */}
      <div className="px-4 pb-1.5 text-[10px] uppercase tracking-widest text-gray-600">
        <span>Code It · Intelligence Console</span>
      </div>
    </header>
  );
}
