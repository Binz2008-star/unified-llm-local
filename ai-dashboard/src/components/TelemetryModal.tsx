import React, { useEffect } from 'react';
import { X, Cpu, HardDrive, MemoryStick, Activity, Database, CheckCircle2, Server } from 'lucide-react';
import { SystemTelemetry, SecondBrainProject } from '../types';
import { Language, translations } from '../i18n';

interface TelemetryModalProps {
  isOpen: boolean;
  onClose: () => void;
  telemetry: SystemTelemetry | null;
  projects: SecondBrainProject[];
  currentProjectId: string;
  onSwitchProject: (id: string) => void;
  lang: Language;
}

export const TelemetryModal: React.FC<TelemetryModalProps> = ({
  isOpen,
  onClose,
  telemetry,
  projects,
  currentProjectId,
  onSwitchProject,
  lang,
}) => {
  const t = translations[lang];

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    if (isOpen) {
      window.addEventListener('keydown', handleKeyDown);
    }
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const diskPct = telemetry?.disk.usePct || 80.95;
  const cpuOverall = telemetry?.cpu || 44.8;
  const memUsedGB = ((telemetry?.mem.used || 15107571712) / (1024 ** 3)).toFixed(2);
  const memTotalGB = ((telemetry?.mem.total || 17126236160) / (1024 ** 3)).toFixed(2);
  const memPct = Math.round((Number(memUsedGB) / Number(memTotalGB)) * 100);
  const diskFreeGB = ((telemetry?.disk.free || 91278835712) / (1024 ** 3)).toFixed(1);
  const diskTotalGB = ((telemetry?.disk.total || 479116754944) / (1024 ** 3)).toFixed(1);

  const cores = telemetry?.cpu_cores && telemetry.cpu_cores.length > 0
    ? telemetry.cpu_cores
    : [36, 85, 42, 45, 39, 44, 48, 51, 40, 42, 38, 46];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-black/70 backdrop-blur-xs animate-in fade-in duration-200">
      <div
        className="w-full max-w-2xl bg-[#171716] border border-white/10 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]"
        dir={lang === 'ar' ? 'rtl' : 'ltr'}
      >
        {/* Header */}
        <div className="p-4 bg-[#1b1b1a] border-b border-white/10 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-[#d97757]/15 border border-[#d97757]/30 flex items-center justify-center text-[#d97757] shrink-0">
              <Server className="w-4 h-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-semibold text-stone-100">
                  {t.telemetry.title}
                </h3>
                <span className="text-[10px] font-mono-code px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  {telemetry?.system.host || 'ROBEN'} • {t.telemetry.hostSpecs.split('•')[1]?.trim() || t.connected}
                </span>
              </div>
              <p className="text-[11px] text-stone-400 font-mono">
                {telemetry?.system.os || 'Windows_NT 10.0.26200'} • 12 Cores
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 text-stone-400 hover:text-stone-100 hover:bg-white/5 rounded-lg transition-colors"
            title={t.telemetry.close}
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        <div className="p-4 sm:p-5 overflow-y-auto space-y-4 sm:space-y-5 text-stone-300 text-xs">
          {/* Quick Metrics Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {/* CPU Metric */}
            <div className="p-3.5 rounded-xl bg-white/[0.03] border border-white/5 space-y-2">
              <div className="flex items-center justify-between text-stone-400">
                <span className="flex items-center gap-1.5">
                  <Cpu className="w-3.5 h-3.5 text-[#d97757]" />
                  <span>{t.telemetry.cpu}</span>
                </span>
                <span className="font-mono text-stone-200 font-semibold">{cpuOverall}%</span>
              </div>
              <div className="w-full bg-stone-800 h-1.5 rounded-full overflow-hidden">
                <div
                  className="bg-[#d97757] h-full transition-all duration-500"
                  style={{ width: `${Math.min(cpuOverall, 100)}%` }}
                />
              </div>
              <span className="text-[10px] text-stone-500 font-mono block">{t.telemetry.cpuHot}</span>
            </div>

            {/* RAM Metric */}
            <div className="p-3.5 rounded-xl bg-white/[0.03] border border-white/5 space-y-2">
              <div className="flex items-center justify-between text-stone-400">
                <span className="flex items-center gap-1.5">
                  <Activity className="w-3.5 h-3.5 text-emerald-400" />
                  <span>{t.telemetry.ram}</span>
                </span>
                <span className="font-mono text-stone-200 font-semibold">{memPct}%</span>
              </div>
              <div className="w-full bg-stone-800 h-1.5 rounded-full overflow-hidden">
                <div
                  className="bg-emerald-500 h-full transition-all duration-500"
                  style={{ width: `${Math.min(memPct, 100)}%` }}
                />
              </div>
              <span className="text-[10px] text-stone-500 font-mono block">
                {memUsedGB} GB {t.telemetry.ramOf} {memTotalGB} GB
              </span>
            </div>

            {/* Disk Metric */}
            <div className="p-3.5 rounded-xl bg-white/[0.03] border border-white/5 space-y-2">
              <div className="flex items-center justify-between text-stone-400">
                <span className="flex items-center gap-1.5">
                  <HardDrive className="w-3.5 h-3.5 text-amber-400" />
                  <span>{t.telemetry.disk}</span>
                </span>
                <span className="font-mono text-amber-400 font-semibold">{diskPct.toFixed(1)}%</span>
              </div>
              <div className="w-full bg-stone-800 h-1.5 rounded-full overflow-hidden">
                <div
                  className="bg-amber-400 h-full transition-all duration-500"
                  style={{ width: `${Math.min(diskPct, 100)}%` }}
                />
              </div>
              <span className="text-[10px] text-stone-500 font-mono block">
                {t.telemetry.diskFree} {diskFreeGB} GB {t.telemetry.ramOf} {diskTotalGB} GB
              </span>
            </div>
          </div>

          {/* 12-Core Load Visualizer */}
          <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/5 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-stone-300">
                {t.telemetry.coresLoad}
              </span>
              <span className="text-[10px] font-mono text-stone-500">{t.telemetry.liveThreads}</span>
            </div>
            <div className="grid grid-cols-6 sm:grid-cols-12 gap-1.5 pt-1">
              {cores.map((load, idx) => (
                <div key={idx} className="flex flex-col items-center gap-1">
                  <div className="w-full bg-stone-900 h-12 rounded-sm relative overflow-hidden flex items-end p-0.5">
                    <div
                      className={`w-full rounded-xs transition-all duration-300 ${
                        load > 75 ? 'bg-rose-500' : load > 50 ? 'bg-[#d97757]' : 'bg-emerald-500'
                      }`}
                      style={{ height: `${load}%` }}
                    />
                  </div>
                  <span className="text-[9px] font-mono text-stone-400">{load}%</span>
                  <span className="text-[8px] font-mono text-stone-600">C{idx + 1}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Connected Second Brain Projects */}
          <div className="space-y-2.5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-stone-300">
                {t.telemetry.secondBrainProjects}
              </span>
              <span className="text-[10px] font-mono text-[#d97757]">
                {t.telemetry.activeNow} {projects.find((p) => p.id === currentProjectId)?.name || currentProjectId}
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {projects.map((proj) => {
                const isActive = proj.id === currentProjectId;
                return (
                  <div
                    key={proj.id}
                    onClick={() => onSwitchProject(proj.id)}
                    className={`p-3 rounded-xl border transition-all cursor-pointer flex flex-col justify-between gap-1.5 ${
                      isActive
                        ? 'bg-[#d97757]/10 border-[#d97757]/40 text-stone-100'
                        : 'bg-white/[0.02] border-white/5 hover:border-white/15 text-stone-400 hover:text-stone-200'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold">{proj.name}</span>
                      {isActive && (
                        <span className="text-[9px] font-mono bg-[#d97757] text-white px-1.5 py-0.2 rounded">
                          {t.active}
                        </span>
                      )}
                    </div>
                    {proj.description && (
                      <p className="text-[10px] text-stone-400 line-clamp-1">{proj.description}</p>
                    )}
                    <div className="flex items-center justify-between text-[9px] font-mono text-stone-500 pt-1 border-t border-white/5">
                      <span className="truncate max-w-[170px]">{proj.path}</span>
                      <span className="text-stone-400">{proj.tech.split('•')[0]}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Persistence & Evolution Status */}
          <div className="p-3 rounded-xl bg-emerald-500/5 border border-emerald-500/15 flex items-center justify-between text-[11px] flex-wrap gap-2">
            <div className="flex items-center gap-2 text-emerald-400">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span>{t.telemetry.vectorDbStatus}</span>
            </div>
            <span className="text-[10px] font-mono text-emerald-500">{t.telemetry.autoEvolution}</span>
          </div>
        </div>

        {/* Footer */}
        <div className="p-3.5 bg-[#141413] border-t border-white/10 flex items-center justify-between">
          <span className="text-[11px] text-stone-500 font-mono">
            Host: ROBEN • JARVIS Multi-Agent Core
          </span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-white/10 hover:bg-white/15 text-stone-200 text-xs font-medium transition-colors"
          >
            {t.telemetry.close}
          </button>
        </div>
      </div>
    </div>
  );
};
