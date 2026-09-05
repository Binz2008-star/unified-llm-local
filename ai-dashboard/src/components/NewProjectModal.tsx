import React, { useState } from 'react';
import { X, Plus, FolderGit2, Sparkles, Check, Server, Terminal, Laptop } from 'lucide-react';
import { Language } from '../i18n';
import { SecondBrainProject } from '../types';

interface NewProjectModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreateProject: (project: { name: string; path: string; tech: string; description: string }) => Promise<void>;
  lang: Language;
}

export const NewProjectModal: React.FC<NewProjectModalProps> = ({
  isOpen,
  onClose,
  onCreateProject,
  lang,
}) => {
  const [name, setName] = useState('');
  const [path, setPath] = useState('X:\\workspace\\');
  const [tech, setTech] = useState('Python 3.11 • FastAPI • Neon DB');
  const [description, setDescription] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');

  if (!isOpen) return null;

  const handleNameChange = (val: string) => {
    setName(val);
    setError('');
    // Auto-update path slug if user hasn't heavily customized it
    const slug = val
      .toLowerCase()
      .replace(/[^a-z0-9]/g, '-')
      .replace(/-+/g, '-')
      .replace(/(^-|-$)/g, '');
    if (slug) {
      setPath(`X:\\workspace\\${slug}`);
    }
  };

  const applyPreset = (preset: { name: string; tech: string; desc: string; pathPrefix?: string }) => {
    setName(preset.name);
    setTech(preset.tech);
    setDescription(preset.desc);
    const slug = preset.name.toLowerCase().replace(/[^a-z0-9]/g, '-').replace(/-+/g, '-');
    setPath(`X:\\workspace\\${slug}`);
    setError('');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmedName = name.trim();
    if (!trimmedName) {
      setError(lang === 'ar' ? 'يرجى إدخال اسم المشروع' : 'Please enter a project name');
      return;
    }

    setIsSubmitting(true);
    setError('');
    try {
      await onCreateProject({
        name: trimmedName,
        path: path.trim() || `X:\\workspace\\${trimmedName.toLowerCase()}`,
        tech: tech.trim() || 'Python • TypeScript',
        description: description.trim() || (lang === 'ar' ? 'مشروع جديد في Second Brain' : 'New Second Brain project'),
      });
      setName('');
      setDescription('');
      onClose();
    } catch (err: any) {
      setError(err?.message || (lang === 'ar' ? 'حدث خطأ أثناء إنشاء المشروع' : 'Failed to create project'));
    } finally {
      setIsSubmitting(false);
    }
  };

  const presets = [
    {
      name: 'Autonomous Agent',
      tech: 'Python 3.11 • FastEmbed • Neon DB',
      desc: lang === 'ar' ? 'وكيل ذكي مستقل لمعالجة البيانات والتفاعل مع الذاكرة' : 'Autonomous AI agent with vector retrieval and memory',
    },
    {
      name: 'Cloud Microservice',
      tech: 'TypeScript • Node.js • Express • Redis',
      desc: lang === 'ar' ? 'خدمة سحابية عالية الأداء مع حماية Circuit Breaker' : 'High-throughput microservice with Circuit Breaker and cache',
    },
    {
      name: 'Content & Media Engine',
      tech: 'Python • FFMPEG • Ollama 768d',
      desc: lang === 'ar' ? 'محرك ذكي لمعالجة الوسائط والنشر المتعدد' : 'Media processing, automated generation and multi-platform publishing',
    },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-black/75 backdrop-blur-sm fade-in">
      <div className="fixed inset-0" onClick={onClose} />

      <div
        id="new-project-modal"
        className="relative bg-[#1b1b1a] border border-white/10 rounded-2xl w-full max-w-xl shadow-2xl overflow-hidden z-10"
        dir={lang === 'ar' ? 'rtl' : 'ltr'}
      >
        {/* Modal Header */}
        <div className="p-4 sm:p-5 border-b border-white/[0.08] flex items-center justify-between bg-white/[0.02]">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-[#d97757]/15 border border-[#d97757]/30 flex items-center justify-center text-[#d97757]">
              <FolderGit2 className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm sm:text-base font-semibold text-stone-100 flex items-center gap-2">
                <span>{lang === 'ar' ? 'إضافة مشروع جديد إلى Second Brain' : 'Create New Second Brain Project'}</span>
                <span className="text-[10px] font-mono-code bg-[#d97757]/10 text-[#d97757] px-2 py-0.5 rounded border border-[#d97757]/20">
                  + New
                </span>
              </h2>
              <p className="text-[11px] text-stone-400">
                {lang === 'ar'
                  ? 'ربط مجلد كود محلي أو بيئة عمل جديدة بمحرك الذكاء الاصطناعي وذاكرة المضيف ROBEN'
                  : 'Register a new local workspace or code repository with Second Brain intelligence & memory'}
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

        {/* Presets Row */}
        <div className="px-4 sm:px-5 pt-3 pb-1 border-b border-white/[0.05] bg-black/20">
          <div className="text-[10px] font-mono text-stone-500 uppercase tracking-wider mb-2">
            {lang === 'ar' ? 'قوالب سريعة جاهزة:' : 'Quick Project Presets:'}
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 pb-3">
            {presets.map((preset, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => applyPreset(preset)}
                className={`p-2 rounded-xl bg-white/[0.03] hover:bg-white/[0.08] border border-white/5 hover:border-[#d97757]/30 text-xs transition-all ${
                  lang === 'ar' ? 'text-right' : 'text-left'
                }`}
              >
                <div className="font-semibold text-stone-200 truncate">{preset.name}</div>
                <div className="text-[10px] text-stone-400 font-mono truncate mt-0.5">{preset.tech.split('•')[0]}</div>
              </button>
            ))}
          </div>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-4 sm:p-5 space-y-3.5">
          {error && (
            <div className="p-2.5 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-rose-400" />
              <span>{error}</span>
            </div>
          )}

          {/* Project Name */}
          <div className="space-y-1">
            <label className="text-xs font-medium text-stone-300 flex items-center justify-between">
              <span>{lang === 'ar' ? 'اسم المشروع *' : 'Project Name *'}</span>
              <span className="text-[10px] text-stone-500 font-mono">e.g. Fintech Routing Engine</span>
            </label>
            <input
              type="text"
              required
              value={name}
              onChange={(e) => handleNameChange(e.target.value)}
              placeholder={lang === 'ar' ? 'مثال: نظام التحقق الذكي' : 'e.g., Payment Gateway Agent'}
              className="w-full bg-white/[0.04] border border-white/10 rounded-xl px-3 py-2 text-stone-100 text-xs focus:border-[#d97757] focus:ring-1 focus:ring-[#d97757] outline-none transition-colors"
            />
          </div>

          {/* Local Path on Host */}
          <div className="space-y-1">
            <label className="text-xs font-medium text-stone-300 flex items-center justify-between">
              <span>{lang === 'ar' ? 'المسار المحلي على المضيف (Host Path)' : 'Local Host Path'}</span>
              <span className="text-[10px] text-stone-500 font-mono">Host: ROBEN (Windows)</span>
            </label>
            <div className="relative">
              <input
                type="text"
                value={path}
                onChange={(e) => setPath(e.target.value)}
                placeholder="X:\workspace\my-project"
                className="w-full bg-white/[0.04] border border-white/10 rounded-xl px-3 py-2 text-stone-200 text-xs font-mono focus:border-[#d97757] outline-none transition-colors"
                dir="ltr"
              />
            </div>
          </div>

          {/* Tech Stack */}
          <div className="space-y-1">
            <label className="text-xs font-medium text-stone-300 flex items-center justify-between">
              <span>{lang === 'ar' ? 'التقنيات المستخدمة (Tech Stack)' : 'Tech Stack'}</span>
              <span className="text-[10px] text-stone-500 font-mono">e.g. Python • Neon • FastEmbed</span>
            </label>
            <input
              type="text"
              value={tech}
              onChange={(e) => setTech(e.target.value)}
              placeholder="Python 3.11 • FastEmbed • Neon DB"
              className="w-full bg-white/[0.04] border border-white/10 rounded-xl px-3 py-2 text-stone-200 text-xs font-mono focus:border-[#d97757] outline-none transition-colors"
              dir="ltr"
            />
          </div>

          {/* Description */}
          <div className="space-y-1">
            <label className="text-xs font-medium text-stone-300">
              {lang === 'ar' ? 'وصف المشروع ودوره' : 'Project Description & Objectives'}
            </label>
            <textarea
              rows={2}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder={lang === 'ar' ? 'وصف مختصر لأهداف المشروع ومتطلباته...' : 'Brief description of project architecture and requirements...'}
              className="w-full bg-white/[0.04] border border-white/10 rounded-xl px-3 py-2 text-stone-200 text-xs focus:border-[#d97757] outline-none transition-colors resize-none"
            />
          </div>

          {/* Action Buttons */}
          <div className="pt-3 border-t border-white/[0.08] flex items-center justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-3.5 py-2 rounded-xl text-stone-400 hover:text-stone-200 hover:bg-white/5 text-xs transition-colors"
            >
              {lang === 'ar' ? 'إلغاء' : 'Cancel'}
            </button>
            <button
              type="submit"
              disabled={isSubmitting || !name.trim()}
              className={`px-4 py-2 rounded-xl text-white text-xs font-medium flex items-center gap-1.5 shadow-lg shadow-[#d97757]/20 transition-all ${
                isSubmitting || !name.trim()
                  ? 'bg-stone-700 opacity-60 cursor-not-allowed'
                  : 'bg-[#d97757] hover:bg-[#c26648] active:scale-95'
              }`}
            >
              <Plus className="w-3.5 h-3.5" />
              <span>
                {isSubmitting
                  ? lang === 'ar' ? 'جاري الإنشاء...' : 'Creating...'
                  : lang === 'ar' ? 'إنشاء المشروع والربط' : 'Create & Connect Project'}
              </span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
