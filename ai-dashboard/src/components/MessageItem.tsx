import React, { useState } from 'react';
import {
  Copy,
  Check,
  Code2,
  Sparkles,
  Search,
  Compass,
  Cpu,
  Terminal,
  BrainCircuit,
  FileCode,
} from 'lucide-react';
import { Message, CodeArtifact, AgentPhase } from '../types';
import { Language, translations } from '../i18n';

interface MessageItemProps {
  message: Message;
  onOpenArtifact: (artifact: CodeArtifact) => void;
  lang: Language;
}

export const MessageItem: React.FC<MessageItemProps> = ({
  message,
  onOpenArtifact,
  lang,
}) => {
  const [copied, setCopied] = useState(false);
  const t = translations[lang];

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const getPhaseIcon = (name: AgentPhase['name']) => {
    switch (name) {
      case 'researcher':
        return <Search className="w-3 h-3 text-cyan-400" />;
      case 'architect':
        return <Compass className="w-3 h-3 text-amber-400" />;
      case 'editor':
        return <Cpu className="w-3 h-3 text-[#d97757]" />;
      case 'tester':
        return <Terminal className="w-3 h-3 text-emerald-400" />;
      case 'memory':
        return <BrainCircuit className="w-3 h-3 text-purple-400" />;
      default:
        return <Check className="w-3 h-3 text-emerald-400" />;
    }
  };

  const getPhaseLabel = (name: AgentPhase['name'], defaultLabel: string) => {
    return t.message.phases[name] || defaultLabel;
  };

  if (message.role === 'user') {
    return (
      <div className="space-y-2 fade-in" id={`msg-${message.id}`}>
        <div className={`flex items-center gap-2 ${lang === 'ar' ? 'justify-start' : 'justify-end'}`}>
          <span className="text-[11px] font-mono-code text-stone-500 uppercase tracking-wider">
            {lang === 'ar' ? 'أنت' : 'You'}
          </span>
          <span className="text-[10px] text-stone-600 font-mono-code">
            {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </span>
        </div>

        <div className={`flex ${lang === 'ar' ? 'justify-start' : 'justify-end'}`}>
          <div className="bg-[#1e1e1c] border border-white/[0.08] text-stone-100 rounded-2xl p-4 max-w-[85%] text-[15px] leading-relaxed shadow-sm">
            <p className="whitespace-pre-wrap font-sans">{message.content}</p>

            {message.attachedFiles && message.attachedFiles.length > 0 && (
              <div className="mt-3 pt-2.5 border-t border-white/5 flex flex-wrap gap-1.5">
                {message.attachedFiles.map((f, idx) => (
                  <span
                    key={idx}
                    className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-white/5 text-[11px] font-mono-code text-stone-400 border border-white/5"
                  >
                    <FileCode className="w-3 h-3 text-[#d97757]" />
                    <span>{f.name}</span>
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  // Assistant Message
  return (
    <div className="space-y-3 fade-in group" id={`msg-${message.id}`}>
      {/* Header Info */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-mono-code text-[#d97757] uppercase tracking-widest block font-medium">
            Second Brain Multi-Agent Core
          </span>
          {message.modelSource && (
            <span className="text-[9px] font-mono-code bg-white/5 text-stone-400 px-1.5 py-0.5 rounded border border-white/5">
              {message.modelSource}
            </span>
          )}
        </div>

        <button
          onClick={handleCopy}
          className="opacity-0 group-hover:opacity-100 p-1 text-stone-400 hover:text-stone-200 transition-opacity rounded hover:bg-white/5"
          title={t.message.copy}
        >
          {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
        </button>
      </div>

      {/* Multi-Agent Pipeline Phases (Second Brain v4) */}
      {message.agentPhases && message.agentPhases.length > 0 ? (
        <div className="bg-white/[0.02] border border-white/[0.08] rounded-xl p-3.5 space-y-2.5">
          <div className="text-[11px] text-stone-400 font-medium flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-500" />
              <span className="text-stone-200 font-medium font-mono text-[11px]">
                {t.message.agentPipeline}
              </span>
            </div>
            <span className="text-[10px] font-mono-code text-stone-500">
              5 {t.message.completedPhases}
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2 pt-1">
            {message.agentPhases.map((phase, idx) => (
              <div
                key={idx}
                className="bg-white/[0.03] border border-white/5 rounded-lg p-2 flex flex-col justify-between gap-1"
              >
                <div className="flex items-center gap-1.5 text-stone-200 text-xs font-medium">
                  {getPhaseIcon(phase.name)}
                  <span className="truncate">{getPhaseLabel(phase.name, phase.label)}</span>
                </div>
                {phase.detail && (
                  <span className="text-[10px] text-stone-400 line-clamp-1 font-sans">
                    {phase.detail}
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      ) : message.thinkingSteps && message.thinkingSteps.length > 0 ? (
        /* Thinking Steps Container fallback */
        <div className="bg-white/[0.02] border border-white/[0.08] rounded-xl p-3.5 space-y-2.5">
          <div className="text-[11px] text-stone-400 font-medium flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span
                className={`w-2 h-2 rounded-full ${
                  message.isThinking ? 'bg-[#d97757] animate-pulse' : 'bg-emerald-500'
                }`}
              />
              <span className="text-stone-300 font-medium">
                {message.isThinking ? t.message.thinkingActive : t.message.thinkingCompleted}
              </span>
            </div>
            <span className="text-[10px] font-mono-code text-stone-500">
              {message.thinkingSteps.length} {lang === 'ar' ? 'خطوات' : 'steps'}
            </span>
          </div>

          <div className="space-y-1.5 pt-1">
            {message.thinkingSteps.map((step, idx) => (
              <div key={idx} className="text-xs text-stone-400 flex items-start gap-2 leading-relaxed">
                <span className="text-[10px] font-mono-code text-stone-600 mt-0.5">0{idx + 1}.</span>
                <span>{step}</span>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {/* Primary Response Content */}
      <div className="text-[15px] text-stone-300 leading-relaxed font-serif-anthropic space-y-2">
        {message.content ? (
          <p className="whitespace-pre-wrap">{message.content}</p>
        ) : message.isThinking ? (
          <div className="flex items-center gap-2 text-stone-400 text-sm py-1">
            <Sparkles className="w-4 h-4 text-[#d97757] animate-pulse" />
            <span>{t.message.generatingResponse}</span>
          </div>
        ) : null}

        {/* Executed System Action Badge */}
        {message.systemAction?.executedNotice && (
          <div className="pt-1">
            <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-emerald-500/10 border border-emerald-500/25 text-emerald-400 text-xs font-mono">
              <Check className="w-3.5 h-3.5" />
              <span>{message.systemAction.executedNotice}</span>
            </div>
          </div>
        )}
      </div>

      {/* Embedded Artifact Card */}
      {message.artifact && (
        <div className="pt-2">
          <div
            onClick={() => onOpenArtifact(message.artifact!)}
            className="group/art cursor-pointer bg-[#1b1b1a] border border-white/10 hover:border-[#d97757]/40 rounded-xl p-3.5 transition-all shadow-md flex items-center justify-between"
          >
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-[#d97757]/15 border border-[#d97757]/30 flex items-center justify-center text-[#d97757] group-hover/art:scale-105 transition-transform">
                <Code2 className="w-4 h-4" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold text-stone-200 font-mono-code">
                    {message.artifact.title}
                  </span>
                  <span className="text-[10px] font-mono-code uppercase px-2 py-0.5 rounded bg-white/5 text-stone-400 border border-white/5">
                    {message.artifact.language}
                  </span>
                  {message.artifact.projectId && (
                    <span className="text-[9px] font-mono-code text-[#d97757] bg-[#d97757]/10 px-1.5 py-0.5 rounded">
                      {t.message.projectBadge}: {message.artifact.projectId}
                    </span>
                  )}
                </div>
                <p className="text-[11px] text-stone-400 mt-0.5">
                  {message.artifact.description || t.message.interactiveFile}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-xs text-[#d97757] font-medium hidden sm:inline group-hover/art:underline">
                {t.message.inspectCode}
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
