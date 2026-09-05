/**
 * Code It - Intelligence Console / ROBEN AI OS Dashboard
 * Sidebar.tsx - Navigation Sidebar with status widgets and workspace routing
 *
 * Author: Second Brain KB Team
 * License: MIT
 */

import React from "react";
import { useApp } from "../context/AppContext";

// ---------------------------------------------------------------------------
//  Navigation Items
// ---------------------------------------------------------------------------

interface NavItem {
  id: string;
  label: string;
  icon: React.ReactNode;
  badge?: string | number;
  badgeColor?: string;
}

const NAV_ICONS = {
  dashboard: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4">
      <rect x="3" y="3" width="7" height="9" rx="1" />
      <rect x="14" y="3" width="7" height="5" rx="1" />
      <rect x="14" y="12" width="7" height="9" rx="1" />
      <rect x="3" y="16" width="7" height="5" rx="1" />
    </svg>
  ),
  chat: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4">
      <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" />
    </svg>
  ),
  review: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4">
      <path d="M16 18l6-6-4-4a4 4 0 0 0-8 0L2 16v6h6l4-4" />
      <circle cx="8" cy="8" r="1" />
      <circle cx="16" cy="16" r="1" />
    </svg>
  ),
  memory: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4">
      <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
    </svg>
  ),
  projects: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4">
      <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
    </svg>
  ),
  settings: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4">
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
    </svg>
  ),
} as const;

// ---------------------------------------------------------------------------
//  Status Widgets
// ---------------------------------------------------------------------------

function StatusWidgets() {
  const { telemetry, telemetryError } = useApp();

  const cpu = `${(telemetry?.cpu?.totalPercent ?? 0).toFixed(0)}%`;
  const mem = `${((telemetry?.memory?.usedBytes ?? 0) / (telemetry?.memory?.totalBytes || 1)) * 100 <= 100 ? Math.round(((telemetry?.memory?.usedBytes ?? 0) / (telemetry?.memory?.totalBytes || 1)) * 100) : '--'}%`;

  const isOffline = telemetryError || !telemetry;

  return (
    <div className="px-3 space-y-2" dir="ltr">
      <div className="flex items-center justify-between text-[11px]">
        <span className="text-gray-500 uppercase tracking-wider">System</span>
        <span className={`flex items-center gap-1.5 ${isOffline ? "text-red-400" : "text-emerald-400"}`}>
          <span className={`w-1.5 h-1.5 rounded-full ${isOffline ? "bg-red-400" : "bg-emerald-400 animate-pulse"}`} />
          {isOffline ? "OFF" : "ON"}
        </span>
      </div>

      <div className="space-y-1.5">
        {/* CPU Bar */}
        <div>
          <div className="flex justify-between text-[10px] text-gray-500 mb-0.5" dir="ltr">
            <span>CPU</span>
            <span>{cpu}</span>
          </div>
          <div className="h-1.5 bg-white/10 rounded-full overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-500"
              style={{
                width: `${Math.min(100, telemetry?.cpu?.totalPercent ?? 0)}%`,
                background: cpuColor(telemetry?.cpu?.totalPercent ?? 0),
              }}
            />
          </div>
        </div>

        {/* Memory Bar */}
        <div>
          <div className="flex justify-between text-[10px] text-gray-500 mb-0.5" dir="ltr">
            <span>MEM</span>
            <span>{mem}</span>
          </div>
          <div className="h-1.5 bg-white/10 rounded-full overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-500"
              style={{
                width: `${Math.min(100, (telemetry?.memory?.percent ?? 0))}%`,
                background: cpuColor(telemetry?.memory?.percent ?? 0),
              }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

function cpuColor(percent: number): string {
  if (percent < 50) return "#22c55e";
  if (percent < 80) return "#eab308";
  return "#ef4444";
}

// ---------------------------------------------------------------------------
//  Sidebar Main Component
// ---------------------------------------------------------------------------

export default function Sidebar() {
  const {
    activeView,
    setActiveView,
    sidebarOpen,
    setSidebarOpen,
    pushNotification,
    activeProject,
  } = useApp();

  const navItems: NavItem[] = [
    { id: "dashboard", label: "Dashboard", icon: NAV_ICONS.dashboard },
    { id: "chat", label: "Agent Chat", icon: NAV_ICONS.chat },
    { id: "review", label: "Code Review", icon: NAV_ICONS.review },
    { id: "memory", label: "Memory", icon: NAV_ICONS.memory },
    { id: "projects", label: "Projects", icon: NAV_ICONS.projects },
    { id: "settings", label: "Settings", icon: NAV_ICONS.settings },
  ];

  const handleNav = (id: string) => {
    setActiveView(id);
    if (id !== "dashboard") {
      pushNotification("info", "Navigation", `Opened: ${id}`, true);
    }
  };

  const toggleSidebar = () => setSidebarOpen(!sidebarOpen);

  return (
    <>
      {/* Collapsed toggle button */}
      {!sidebarOpen && (
        <button
          type="button"
          onClick={toggleSidebar}
          className="fixed left-3 top-4 z-50 p-2 bg-white/5 border border-white/10 rounded-lg text-gray-300 hover:text-cyan-400 hover:border-cyan-500/40 transition-colors"
          title="Open Sidebar"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5">
            <line x1="4" y1="9" x2="20" y2="9" />
            <line x1="4" y1="15" x2="20" y2="15" />
            <line x1="10" y1="3" x2="8" y2="21" />
            <line x1="16" y1="3" x2="14" y2="21" />
          </svg>
        </button>
      )}

      <aside
        className={`fixed left-0 top-0 bottom-0 z-40 w-64 bg-[#0a0f1c]/95 backdrop-blur border-r border-white/10 flex flex-col transition-transform duration-300 ${sidebarOpen ? "translate-x-0" : "-translate-x-full"
          }`}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-4 border-b border-white/10">
          <div className="flex items-center gap-2" dir="ltr">
            <span className="text-xl">🧠</span>
            <div>
              <div className="text-sm font-bold text-white leading-tight" dir="ltr" style={{ fontFamily: '"IBM Plex Mono", "Cairo", sans-serif' }}>
                ROBEN AI OS
              </div>
              <div className="text-[10px] text-gray-500 tracking-wider" dir="ltr" style={{ fontFamily: '"IBM Plex Mono", "Cairo", sans-serif' }}>
                INTELLIGENCE CONSOLE
              </div>
            </div>
          </div>
          <button
            type="button"
            onClick={toggleSidebar}
            className="p-1 text-gray-400 hover:text-white transition-colors"
            title="Close Sidebar"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        {/* Active Project Chip */}
        <div className="px-3 pt-3" dir="ltr">
          <div className="flex items-center gap-2 px-3 py-2 bg-gradient-to-r from-cyan-500/10 to-violet-500/10 border border-white/10 rounded-lg">
            <span className="text-lg">📁</span>
            <div className="min-w-0">
              <div className="text-[9px] uppercase tracking-widest text-gray-500" style={{ fontFamily: '"IBM Plex Mono", "Cairo", sans-serif' }}>
                Active Project
              </div>
              <div className="text-sm text-cyan-100 truncate" style={{ fontFamily: '"IBM Plex Mono", "Cairo", sans-serif' }}>
                {activeProject ? activeProject : "None"}
              </div>
            </div>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto px-2 py-3" aria-label="Primary">
          <div className="px-3 py-1 text-[9px] uppercase tracking-widest text-gray-600" style={{ fontFamily: '"IBM Plex Mono", "Cairo", sans-serif' }}>
            Workspace
          </div>
          {navItems.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => handleNav(item.id)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 my-0.5 rounded-lg text-sm transition-all ${activeView === item.id
                ? "bg-cyan-500/10 text-cyan-300 border border-cyan-500/30"
                : "text-gray-400 hover:bg-white/5 hover:text-gray-200 border border-transparent"
                }`}
              title={item.label}
            >
              <span className={activeView === item.id ? "text-cyan-400" : ""}>
                {item.icon}
              </span>
              <span className="flex-1 text-left" style={{ fontFamily: '"IBM Plex Mono", "Cairo", sans-serif' }}>
                {item.label}
              </span>
              {item.badge && (
                <span
                  className="text-[9px] px-1.5 py-0.5 rounded-full font-semibold"
                  style={{
                    color: item.badgeColor ?? "#22d3ee",
                    backgroundColor: `${item.badgeColor ?? "#22d3ee"}22`,
                  }}
                >
                  {item.badge}
                </span>
              )}
              {activeView === item.id && (
                <span className="w-1 h-4 bg-cyan-400 rounded-full" />
              )}
            </button>
          ))}
        </nav>

        {/* Status widgets */}
        <div className="px-3 py-3 border-t border-white/10">
          <StatusWidgets />
        </div>

        {/* Footer */}
        <div className="px-4 py-3 border-t border-white/10">
          <div className="flex items-center justify-between text-[10px] text-gray-600" dir="ltr" style={{ fontFamily: '"IBM Plex Mono", "Cairo", sans-serif' }}>
            <span>SB-KB v4</span>
            <span>DeepSeek R1</span>
          </div>
        </div>
      </aside>
    </>
  );
}
