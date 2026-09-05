import React, { useState } from 'react';
import {
  X,
  Settings as SettingsIcon,
  Globe,
  Sliders,
  Cpu,
  Database,
  Github,
  Trash2,
  Check,
  Eye,
  Shield,
  Zap,
  Layout,
  Terminal,
} from 'lucide-react';
import { Language, translations } from '../i18n';
import { ReasoningMode, AppSettings, SystemTelemetry } from '../types';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  settings: AppSettings;
  onUpdateSettings: (newSettings: Partial<AppSettings>) => void;
  onClearStorage: () => void;
  lang: Language;
  telemetry: SystemTelemetry | null;
}

type TabType = 'general' | 'github' | 'ai' | 'interface' | 'storage' | 'system';

export const SettingsModal: React.FC<SettingsModalProps> = ({
  isOpen,
  onClose,
  settings,
  onUpdateSettings,
  onClearStorage,
  lang,
  telemetry,
}) => {
  const [activeTab, setActiveTab] = useState<TabType>('general');
  const [tempToken, setTempToken] = useState<string>(settings.githubToken || '');
  const [savedFeedback, setSavedFeedback] = useState(false);
  const t = translations[lang];

  if (!isOpen) return null;

  const handleSaveGithubToken = () => {
    onUpdateSettings({ githubToken: tempToken.trim() });
    setSavedFeedback(true);
    setTimeout(() => setSavedFeedback(false), 2000);
  };

  const tabs: Array<{ id: TabType; label: string; icon: React.ComponentType<{ className?: string }> }> = [
    { id: 'general', label: t.settings.tabs.general, icon: Sliders },
    { id: 'github', label: t.settings.tabs.github, icon: Github },
    { id: 'ai', label: t.settings.tabs.ai, icon: Zap },
    { id: 'interface', label: t.settings.tabs.interface, icon: Layout },
    { id: 'storage', label: t.settings.tabs.storage, icon: Database },
    { id: 'system', label: t.settings.tabs.system, icon: Cpu },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
      <div
        className="relative w-full max-w-2xl bg-[#181816] border border-white/10 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]"
        dir={lang === 'ar' ? 'rtl' : 'ltr'}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-white/5 bg-[#1f1f1d]">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-[#d97757]/15 border border-[#d97757]/30 flex items-center justify-center text-[#d97757]">
              <SettingsIcon className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-stone-100">{t.settings.title}</h2>
              <p className="text-[11px] text-stone-400">{t.settings.subtitle}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-stone-400 hover:text-white hover:bg-white/5 transition-colors"
            title="Close"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Navigation Tabs */}
        <div className="flex items-center gap-1 px-4 py-2 border-b border-white/5 bg-[#141413] overflow-x-auto no-scrollbar">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-colors ${
                  isActive
                    ? 'bg-[#d97757]/15 text-[#d97757] border border-[#d97757]/30'
                    : 'text-stone-400 hover:text-stone-200 hover:bg-white/5'
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>

        {/* Tab Content Body */}
        <div className="p-5 overflow-y-auto space-y-5 text-stone-300 text-xs leading-relaxed flex-1">
          {/* GENERAL TAB */}
          {activeTab === 'general' && (
            <div className="space-y-4">
              <div className="space-y-2">
                <label className="text-xs font-semibold text-stone-200 flex items-center gap-2">
                  <Globe className="w-3.5 h-3.5 text-[#d97757]" />
                  <span>{t.settings.language}</span>
                </label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => onUpdateSettings({ language: 'ar' })}
                    className={`p-3 rounded-xl border text-center transition-all ${
                      settings.language === 'ar'
                        ? 'border-[#d97757] bg-[#d97757]/10 text-white font-semibold'
                        : 'border-white/5 bg-white/[0.02] text-stone-400 hover:bg-white/5'
                    }`}
                  >
                    العربية (RTL)
                  </button>
                  <button
                    type="button"
                    onClick={() => onUpdateSettings({ language: 'en' })}
                    className={`p-3 rounded-xl border text-center transition-all ${
                      settings.language === 'en'
                        ? 'border-[#d97757] bg-[#d97757]/10 text-white font-semibold'
                        : 'border-white/5 bg-white/[0.02] text-stone-400 hover:bg-white/5'
                    }`}
                  >
                    English (LTR)
                  </button>
                </div>
              </div>

              <div className="space-y-2 pt-2">
                <label className="text-xs font-semibold text-stone-200 flex items-center gap-2">
                  <Zap className="w-3.5 h-3.5 text-amber-400" />
                  <span>{t.settings.reasoningMode}</span>
                </label>
                <div className="grid grid-cols-3 gap-2">
                  {(['fast', 'advanced', 'security'] as ReasoningMode[]).map((mode) => (
                    <button
                      key={mode}
                      type="button"
                      onClick={() => onUpdateSettings({ reasoningMode: mode })}
                      className={`p-2.5 rounded-xl border text-center transition-all ${
                        settings.reasoningMode === mode
                          ? 'border-[#d97757] bg-[#d97757]/10 text-white font-semibold'
                          : 'border-white/5 bg-white/[0.02] text-stone-400 hover:bg-white/5'
                      }`}
                    >
                      <div className="capitalize text-xs font-medium">
                        {mode === 'fast'
                          ? t.modes.fast.label
                          : mode === 'advanced'
                          ? t.modes.advanced.label
                          : t.modes.security.label}
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* GITHUB TAB */}
          {activeTab === 'github' && (
            <div className="space-y-4">
              <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/5 space-y-2">
                <div className="flex items-center gap-2 text-stone-100 font-medium">
                  <Github className="w-4 h-4 text-[#d97757]" />
                  <span>{t.github.title}</span>
                </div>
                <p className="text-[11px] text-stone-400">{t.settings.githubTokenDesc}</p>
              </div>

              <div className="space-y-2">
                <label className="text-xs font-semibold text-stone-200">
                  {t.settings.githubToken}
                </label>
                <input
                  type="password"
                  value={tempToken}
                  onChange={(e) => setTempToken(e.target.value)}
                  placeholder={t.settings.githubTokenPlaceholder}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-[#141413] border border-white/10 focus:border-[#d97757] text-stone-200 text-xs font-mono placeholder:text-stone-600 outline-none transition-colors"
                />
                <div className="flex items-center justify-between pt-2">
                  <span className="text-[11px] text-stone-500">
                    {tempToken ? '●●●●●●●● (Token configured)' : 'No personal token (Unauthenticated 60 req/hr)'}
                  </span>
                  <button
                    type="button"
                    onClick={handleSaveGithubToken}
                    className="px-4 py-2 rounded-xl bg-[#d97757] hover:bg-[#c66848] text-white font-medium text-xs flex items-center gap-1.5 transition-colors"
                  >
                    {savedFeedback ? <Check className="w-3.5 h-3.5" /> : null}
                    <span>{savedFeedback ? t.settings.saved : t.settings.save}</span>
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* AI ENGINE TAB */}
          {activeTab === 'ai' && (
            <div className="space-y-4">
              <div className="space-y-2">
                <label className="text-xs font-semibold text-stone-200">
                  {t.settings.explanationStyle}
                </label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => onUpdateSettings({ explanationStyle: 'concise' })}
                    className={`p-3 rounded-xl border text-start transition-all ${
                      settings.explanationStyle === 'concise'
                        ? 'border-[#d97757] bg-[#d97757]/10 text-white'
                        : 'border-white/5 bg-white/[0.02] text-stone-400 hover:bg-white/5'
                    }`}
                  >
                    <div className="font-semibold text-xs text-stone-100">{t.settings.styleConcise}</div>
                    <div className="text-[10px] text-stone-400 mt-1">
                      {lang === 'ar' ? 'إجابات مركزة وهيكلية ومباشرة بدون إطالة' : 'Compact, direct code and technical answers'}
                    </div>
                  </button>

                  <button
                    type="button"
                    onClick={() => onUpdateSettings({ explanationStyle: 'detailed' })}
                    className={`p-3 rounded-xl border text-start transition-all ${
                      settings.explanationStyle === 'detailed'
                        ? 'border-[#d97757] bg-[#d97757]/10 text-white'
                        : 'border-white/5 bg-white/[0.02] text-stone-400 hover:bg-white/5'
                    }`}
                  >
                    <div className="font-semibold text-xs text-stone-100">{t.settings.styleDetailed}</div>
                    <div className="text-[10px] text-stone-400 mt-1">
                      {lang === 'ar' ? 'شروحات معمارية مستفيضة مع دراسة حالات الحافة' : 'Comprehensive deep architectural breakdowns'}
                    </div>
                  </button>
                </div>
              </div>

              <div className="p-3 rounded-xl bg-white/[0.02] border border-white/5 space-y-1">
                <div className="text-xs font-medium text-stone-300">Second Brain v4 Multi-Agent Core</div>
                <div className="text-[11px] text-stone-400">
                  {lang === 'ar'
                    ? 'يعتمد النظام تلقائياً على نموذج Gemini 3.8 Flash و Gemini 3.1 Flash Lite مع عزل الخطوات الخمس (Researcher, Architect, Editor, Tester, Memory).'
                    : 'System uses Gemini 3.8 Flash & 3.1 Flash Lite with 5 distinct multi-agent execution phases.'}
                </div>
              </div>
            </div>
          )}

          {/* INTERFACE CLEANLINESS TAB */}
          {activeTab === 'interface' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between p-3.5 rounded-xl bg-white/[0.02] border border-white/5">
                <div className="space-y-0.5 max-w-[80%]">
                  <div className="text-xs font-semibold text-stone-200">{t.settings.showQuickChips}</div>
                  <div className="text-[11px] text-stone-400">{t.settings.showQuickChipsDesc}</div>
                </div>
                <button
                  type="button"
                  onClick={() => onUpdateSettings({ showQuickChips: !settings.showQuickChips })}
                  className={`w-11 h-6 rounded-full transition-colors relative ${
                    settings.showQuickChips ? 'bg-[#d97757]' : 'bg-white/20'
                  }`}
                >
                  <div
                    className={`w-4 h-4 rounded-full bg-white transition-transform absolute top-1 ${
                      settings.showQuickChips ? (lang === 'ar' ? 'left-1' : 'right-1') : (lang === 'ar' ? 'right-1' : 'left-1')
                    }`}
                  />
                </button>
              </div>

              <div className="flex items-center justify-between p-3.5 rounded-xl bg-white/[0.02] border border-white/5">
                <div className="space-y-0.5 max-w-[80%]">
                  <div className="text-xs font-semibold text-stone-200">{t.settings.zenMode}</div>
                  <div className="text-[11px] text-stone-400">{t.settings.zenModeDesc}</div>
                </div>
                <button
                  type="button"
                  onClick={() => onUpdateSettings({ zenMode: !settings.zenMode })}
                  className={`w-11 h-6 rounded-full transition-colors relative ${
                    settings.zenMode ? 'bg-[#d97757]' : 'bg-white/20'
                  }`}
                >
                  <div
                    className={`w-4 h-4 rounded-full bg-white transition-transform absolute top-1 ${
                      settings.zenMode ? (lang === 'ar' ? 'left-1' : 'right-1') : (lang === 'ar' ? 'right-1' : 'left-1')
                    }`}
                  />
                </button>
              </div>
            </div>
          )}

          {/* STORAGE TAB */}
          {activeTab === 'storage' && (
            <div className="space-y-4">
              <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/5 space-y-2">
                <div className="text-xs font-medium text-stone-200">
                  {lang === 'ar' ? 'إدارة التخزين المحلي والذاكرة' : 'Local Storage & Cache Manager'}
                </div>
                <p className="text-[11px] text-stone-400">
                  {lang === 'ar'
                    ? 'يتم حفظ الجلسات وتفضيلاتك محلياً في المتصفح لضمان أمان البيانات والسرعة العالية.'
                    : 'Sessions and user preferences are safely cached in browser local storage.'}
                </p>
              </div>

              <div className="pt-2">
                <button
                  type="button"
                  onClick={() => {
                    if (window.confirm(t.settings.clearStorageConfirm)) {
                      onClearStorage();
                      setSavedFeedback(true);
                      setTimeout(() => setSavedFeedback(false), 2000);
                    }
                  }}
                  className="px-4 py-2.5 rounded-xl bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/20 font-medium text-xs flex items-center gap-2 transition-colors active:scale-98"
                >
                  <Trash2 className="w-4 h-4" />
                  <span>{t.settings.clearStorage}</span>
                </button>
              </div>
            </div>
          )}

          {/* SYSTEM INFO TAB */}
          {activeTab === 'system' && (
            <div className="space-y-3 font-mono text-[11px]">
              <div className="p-3 rounded-xl bg-white/[0.02] border border-white/5 space-y-1.5">
                <div className="text-stone-400">{lang === 'ar' ? 'المضيف:' : 'Host Machine:'}</div>
                <div className="text-stone-100 font-semibold">{telemetry?.system.host || 'ROBEN'} (12 Cores @ 3.4 GHz)</div>
              </div>
              <div className="p-3 rounded-xl bg-white/[0.02] border border-white/5 space-y-1.5">
                <div className="text-stone-400">{lang === 'ar' ? 'الذاكرة RAM:' : 'RAM Status:'}</div>
                <div className="text-stone-100">
                  {telemetry ? `${(telemetry.mem.used / 1024 / 1024 / 1024).toFixed(1)} GB / ${(telemetry.mem.total / 1024 / 1024 / 1024).toFixed(1)} GB` : '11.2 GB / 32.0 GB'}
                </div>
              </div>
              <div className="p-3 rounded-xl bg-white/[0.02] border border-white/5 space-y-1.5">
                <div className="text-stone-400">{lang === 'ar' ? 'الذاكرة المتجهة (Vector Store):' : 'Vector Database:'}</div>
                <div className="text-emerald-400 font-semibold">Neon DB • 768-dim FastEmbed (Connected)</div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-5 py-3 border-t border-white/5 bg-[#141413] flex items-center justify-end">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-xl bg-white/5 hover:bg-white/10 text-stone-200 text-xs font-medium transition-colors"
          >
            {t.telemetry.close}
          </button>
        </div>
      </div>
    </div>
  );
};
