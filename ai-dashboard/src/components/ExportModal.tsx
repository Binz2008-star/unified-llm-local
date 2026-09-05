import React, { useState } from 'react';
import { X, Download, Copy, Check, FileText, Code2, Sparkles, Share2 } from 'lucide-react';
import { Conversation, SecondBrainProject, SystemTelemetry } from '../types';
import { Language } from '../i18n';
import { formatConversationToGFM, downloadFile } from '../utils/exportMarkdown';

interface ExportModalProps {
  isOpen: boolean;
  onClose: () => void;
  conversation: Conversation;
  project?: SecondBrainProject;
  telemetry: SystemTelemetry | null;
  lang: Language;
}

export const ExportModal: React.FC<ExportModalProps> = ({
  isOpen,
  onClose,
  conversation,
  project,
  telemetry,
  lang,
}) => {
  const [copied, setCopied] = useState(false);
  const [activeTab, setActiveTab] = useState<'preview' | 'raw'>('preview');

  if (!isOpen) return null;

  const markdownContent = formatConversationToGFM(conversation, project, telemetry);
  const safeTitle = (conversation.title || 'session')
    .toLowerCase()
    .replace(/[^a-z0-9\u0600-\u06FF]+/g, '_')
    .slice(0, 40);
  const fileName = `${safeTitle || 'code_it_session'}.md`;

  const handleCopy = () => {
    navigator.clipboard.writeText(markdownContent);
    setCopied(true);
    setTimeout(() => setCopied(false), 2200);
  };

  const handleDownloadMarkdown = () => {
    downloadFile(markdownContent, fileName, 'text/markdown;charset=utf-8');
  };

  const handleDownloadJSON = () => {
    const jsonStr = JSON.stringify(conversation, null, 2);
    downloadFile(jsonStr, `${safeTitle || 'code_it_session'}.json`, 'application/json');
  };

  const totalInteractions = Math.ceil(conversation.messages.length / 2);
  const totalArtifacts = conversation.messages.filter((m) => m.artifact).length;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-black/75 backdrop-blur-sm fade-in">
      <div
        className="fixed inset-0"
        onClick={onClose}
      />

      <div
        id="export-modal"
        className="relative bg-[#1b1b1a] border border-white/10 rounded-2xl w-full max-w-3xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden z-10"
        dir={lang === 'ar' ? 'rtl' : 'ltr'}
      >
        {/* Header */}
        <div className="p-4 sm:p-5 border-b border-white/[0.08] flex items-center justify-between bg-white/[0.02]">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-[#d97757]/15 border border-[#d97757]/30 flex items-center justify-center text-[#d97757]">
              <Share2 className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm sm:text-base font-semibold text-stone-100 flex items-center gap-2">
                <span>{lang === 'ar' ? 'تصدير وتوثيق الجلسة (GitHub Flavored Markdown)' : 'Export Session (GitHub Flavored Markdown)'}</span>
                <span className="text-[10px] font-mono-code bg-[#d97757]/10 text-[#d97757] px-2 py-0.5 rounded border border-[#d97757]/20">
                  GFM .md
                </span>
              </h2>
              <p className="text-[11px] text-stone-400">
                {lang === 'ar'
                  ? 'توثيق مهيكل مع تفاصيل الوكلاء، الأكواد المولدة، والمرفقات لمشاركتها مع الفريق على GitHub أو Notion'
                  : 'Structured session log with agent phases, code artifacts, and attached files for GitHub, Slack, or Notion'}
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 text-stone-400 hover:text-stone-100 hover:bg-white/5 rounded-lg transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Stats & Controls Bar */}
        <div className="px-4 py-2.5 bg-black/20 border-b border-white/[0.06] flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-3 font-mono text-[11px] text-stone-400">
            <span>
              {lang === 'ar' ? 'المشروع:' : 'Project:'} <strong className="text-stone-200">{project?.name || 'Second Brain'}</strong>
            </span>
            <span>•</span>
            <span>
              {totalInteractions} {lang === 'ar' ? 'تفاعلات' : 'interactions'}
            </span>
            <span>•</span>
            <span className="text-[#d97757]">
              {totalArtifacts} {lang === 'ar' ? 'ملفات كود' : 'artifacts'}
            </span>
          </div>

          <div className="flex items-center gap-1.5 bg-white/5 p-0.5 rounded-lg border border-white/5">
            <button
              onClick={() => setActiveTab('preview')}
              className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition-colors ${
                activeTab === 'preview'
                  ? 'bg-[#d97757] text-white'
                  : 'text-stone-400 hover:text-stone-200'
              }`}
            >
              {lang === 'ar' ? 'معاينة منسقة' : 'Formatted View'}
            </button>
            <button
              onClick={() => setActiveTab('raw')}
              className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition-colors ${
                activeTab === 'raw'
                  ? 'bg-[#d97757] text-white'
                  : 'text-stone-400 hover:text-stone-200'
              }`}
            >
              {lang === 'ar' ? 'كود Markdown خام' : 'Raw Markdown'}
            </button>
          </div>
        </div>

        {/* Content Viewer */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-5 font-mono text-xs bg-[#141413]">
          {activeTab === 'raw' ? (
            <textarea
              readOnly
              value={markdownContent}
              className="w-full h-80 sm:h-96 bg-black/30 border border-white/5 rounded-xl p-3 text-stone-300 font-mono-code text-[12px] leading-relaxed resize-none outline-none selection:bg-[#d97757]/30"
              dir="ltr"
            />
          ) : (
            <div className="space-y-4 text-stone-300 font-sans text-xs leading-relaxed" dir={lang === 'ar' ? 'rtl' : 'ltr'}>
              <div className="p-3 bg-white/[0.02] border border-white/5 rounded-xl space-y-2">
                <div className="text-sm font-semibold text-stone-100 flex items-center gap-2">
                  <FileText className="w-4 h-4 text-[#d97757]" />
                  <span>{conversation.title}</span>
                </div>
                <div className="text-[11px] text-stone-400">
                  {lang === 'ar'
                    ? 'سيتم تصدير كافة مراحل الوكلاء، الأكواد البرمجية المولدة مع تلوين الصياغة، ومحتويات الملفات المرفقة في ملف Markdown واحد متوافق مع معايير GitHub.'
                    : 'All multi-agent stages, syntax-highlighted code artifacts, and attached file previews are compiled into a unified GFM document.'}
                </div>
              </div>

              {/* Sample GFM Preview Box */}
              <div className="bg-[#1e1e1c] border border-white/10 rounded-xl p-4 font-mono-code text-[11px] text-stone-300 space-y-2 overflow-x-auto" dir="ltr">
                <div className="text-stone-500">// Preview of generated GitHub Flavored Markdown header:</div>
                <div className="text-[#d97757]"># 🚀 Code It Engineering Session: {conversation.title}</div>
                <div className="text-stone-400">| Attribute | Specification |</div>
                <div className="text-stone-400">| :--- | :--- |</div>
                <div className="text-emerald-400/90">| **Target Project** | **{project?.name || 'Second Brain'}** |</div>
                <div className="text-stone-400">| **Tech Stack** | \`{project?.tech || 'Multi-Agent'}\` |</div>
                <div className="text-stone-400">| **Execution Host** | ROBEN (12 Cores, Windows) |</div>
                <div className="text-stone-500 mt-2">... {markdownContent.split('\n').length} lines of structured documentation ...</div>
              </div>
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="p-4 border-t border-white/[0.08] bg-white/[0.02] flex flex-wrap items-center justify-between gap-2.5">
          <div className="flex items-center gap-2">
            <button
              onClick={handleDownloadJSON}
              className="px-3 py-2 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] text-stone-300 hover:text-stone-100 text-xs border border-white/10 flex items-center gap-1.5 transition-colors"
              title={lang === 'ar' ? 'تحميل كملف JSON خام' : 'Download raw JSON backup'}
            >
              <Code2 className="w-3.5 h-3.5 text-stone-400" />
              <span>{lang === 'ar' ? 'نسخة JSON' : 'JSON Backup'}</span>
            </button>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleCopy}
              className="px-3.5 py-2 rounded-xl bg-white/[0.06] hover:bg-white/[0.1] text-stone-200 text-xs border border-white/10 flex items-center gap-1.5 transition-all active:scale-95"
            >
              {copied ? (
                <>
                  <Check className="w-3.5 h-3.5 text-emerald-400" />
                  <span className="text-emerald-400 font-medium">{lang === 'ar' ? 'تم النسخ للحافظة!' : 'Copied to Clipboard!'}</span>
                </>
              ) : (
                <>
                  <Copy className="w-3.5 h-3.5 text-[#d97757]" />
                  <span>{lang === 'ar' ? 'نسخ Markdown' : 'Copy Markdown'}</span>
                </>
              )}
            </button>

            <button
              onClick={handleDownloadMarkdown}
              className="px-4 py-2 rounded-xl bg-[#d97757] hover:bg-[#c26648] text-white text-xs font-medium flex items-center gap-2 shadow-lg shadow-[#d97757]/20 transition-all active:scale-95"
            >
              <Download className="w-3.5 h-3.5" />
              <span>{lang === 'ar' ? 'تحميل ملف .md' : 'Download .md File'}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
