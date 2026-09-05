import React, { useState } from 'react';
import {
  X,
  Github,
  Search,
  Download,
  ExternalLink,
  Star,
  GitFork,
  Code,
  FolderGit2,
  Check,
  AlertCircle,
  Loader2,
  HardDrive,
} from 'lucide-react';
import { Language, translations } from '../i18n';
import { Project } from '../types';

interface GithubRepoDetails {
  name: string;
  fullName: string;
  owner?: string;
  description: string;
  stars: number;
  forks: number;
  openIssues: number;
  language: string;
  defaultBranch: string;
  size: number;
  topics: string[];
  htmlUrl: string;
  zipUrl: string;
  updatedAt?: string;
}

interface GithubModalProps {
  isOpen: boolean;
  onClose: () => void;
  onImportSuccess: (project: Project, repoDetails: GithubRepoDetails) => void;
  lang: Language;
  githubToken?: string;
}

export const GithubModal: React.FC<GithubModalProps> = ({
  isOpen,
  onClose,
  onImportSuccess,
  lang,
  githubToken,
}) => {
  const [repoInput, setRepoInput] = useState('');
  const [isFetching, setIsFetching] = useState(false);
  const [isImporting, setIsImporting] = useState(false);
  const [repoDetails, setRepoDetails] = useState<GithubRepoDetails | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const t = translations[lang];

  if (!isOpen) return null;

  const handleFetchRepo = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!repoInput.trim()) return;

    setIsFetching(true);
    setError(null);
    setRepoDetails(null);
    setSuccessMessage(null);

    try {
      const res = await fetch('/api/github/repo', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url: repoInput.trim(),
          token: githubToken,
        }),
      });

      const data = await res.json();
      if (!res.ok || !data.success) {
        throw new Error(data.error || t.github.errorNotFound);
      }

      setRepoDetails(data.repo);
    } catch (err: any) {
      setError(err.message || t.github.errorNotFound);
    } finally {
      setIsFetching(false);
    }
  };

  const handleImport = async () => {
    if (!repoDetails) return;

    setIsImporting(true);
    setError(null);

    try {
      const res = await fetch('/api/github/import', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url: repoDetails.fullName,
          token: githubToken,
          targetName: repoDetails.name,
        }),
      });

      const data = await res.json();
      if (!res.ok || !data.success) {
        throw new Error(data.error || 'Failed to import repository');
      }

      setSuccessMessage(t.github.importedSuccess);
      setTimeout(() => {
        onImportSuccess(data.newProject, repoDetails);
        onClose();
      }, 1200);
    } catch (err: any) {
      setError(err.message || 'Error during repository import');
    } finally {
      setIsImporting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
      <div
        className="relative w-full max-w-xl bg-[#181816] border border-white/10 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]"
        dir={lang === 'ar' ? 'rtl' : 'ltr'}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-white/5 bg-[#1f1f1d]">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-stone-800 border border-white/10 flex items-center justify-center text-stone-100">
              <Github className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-stone-100">{t.github.title}</h2>
              <p className="text-[11px] text-stone-400">{t.github.subtitle}</p>
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

        {/* Content */}
        <div className="p-5 overflow-y-auto space-y-4 flex-1">
          {/* Input Form */}
          <form onSubmit={handleFetchRepo} className="space-y-2">
            <label className="text-xs font-semibold text-stone-200 block">
              {t.github.inputLabel}
            </label>
            <div className="flex items-center gap-2">
              <div className="relative flex-1">
                <input
                  type="text"
                  value={repoInput}
                  onChange={(e) => setRepoInput(e.target.value)}
                  placeholder={t.github.inputPlaceholder}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-[#141413] border border-white/10 focus:border-[#d97757] text-stone-200 text-xs font-mono placeholder:text-stone-600 outline-none transition-colors"
                />
              </div>
              <button
                type="submit"
                disabled={isFetching || !repoInput.trim()}
                className="px-4 py-2.5 rounded-xl bg-stone-800 hover:bg-stone-700 disabled:opacity-50 text-white font-medium text-xs flex items-center gap-1.5 transition-colors whitespace-nowrap active:scale-98"
              >
                {isFetching ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Search className="w-3.5 h-3.5" />}
                <span>{isFetching ? t.github.fetching : t.github.fetchBtn}</span>
              </button>
            </div>
          </form>

          {/* Error Message */}
          {error && (
            <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Success Message */}
          {successMessage && (
            <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs flex items-center gap-2">
              <Check className="w-4 h-4 shrink-0" />
              <span>{successMessage}</span>
            </div>
          )}

          {/* Repo Details Card */}
          {repoDetails && (
            <div className="p-4 rounded-xl bg-white/[0.02] border border-white/10 space-y-3.5 animate-fade-in">
              <div className="flex items-start justify-between gap-3">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-sm text-stone-100 font-mono">
                      {repoDetails.fullName}
                    </span>
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-stone-800 text-stone-300 border border-white/5">
                      {repoDetails.defaultBranch}
                    </span>
                  </div>
                  <p className="text-xs text-stone-400 line-clamp-2">
                    {repoDetails.description}
                  </p>
                </div>
                <a
                  href={repoDetails.htmlUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="p-2 rounded-lg bg-white/5 hover:bg-white/10 text-stone-300 hover:text-white transition-colors"
                  title={t.github.viewOnGithub}
                >
                  <ExternalLink className="w-3.5 h-3.5" />
                </a>
              </div>

              {/* Stats Bar */}
              <div className="grid grid-cols-4 gap-2 pt-1 border-t border-white/5 text-[11px] text-stone-300">
                <div className="flex items-center gap-1.5 p-2 rounded-lg bg-black/20">
                  <Star className="w-3.5 h-3.5 text-amber-400" />
                  <span>{repoDetails.stars.toLocaleString()}</span>
                </div>
                <div className="flex items-center gap-1.5 p-2 rounded-lg bg-black/20">
                  <GitFork className="w-3.5 h-3.5 text-blue-400" />
                  <span>{repoDetails.forks.toLocaleString()}</span>
                </div>
                <div className="flex items-center gap-1.5 p-2 rounded-lg bg-black/20">
                  <Code className="w-3.5 h-3.5 text-emerald-400" />
                  <span className="truncate">{repoDetails.language}</span>
                </div>
                <div className="flex items-center gap-1.5 p-2 rounded-lg bg-black/20">
                  <HardDrive className="w-3.5 h-3.5 text-purple-400" />
                  <span>{Math.round(repoDetails.size / 1024 * 10) / 10} MB</span>
                </div>
              </div>

              {/* Topics / Tags */}
              {repoDetails.topics && repoDetails.topics.length > 0 && (
                <div className="flex flex-wrap gap-1.5 pt-1">
                  {repoDetails.topics.slice(0, 6).map((topic) => (
                    <span
                      key={topic}
                      className="px-2 py-0.5 rounded-md bg-white/5 text-[10px] text-stone-400 font-mono"
                    >
                      #{topic}
                    </span>
                  ))}
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex items-center gap-2 pt-2 border-t border-white/5">
                <button
                  type="button"
                  onClick={handleImport}
                  disabled={isImporting}
                  className="flex-1 py-2.5 px-4 rounded-xl bg-[#d97757] hover:bg-[#c66848] disabled:opacity-50 text-white font-medium text-xs flex items-center justify-center gap-1.5 transition-colors shadow-lg active:scale-98"
                >
                  {isImporting ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <FolderGit2 className="w-3.5 h-3.5" />
                  )}
                  <span>{t.github.importBtn}</span>
                </button>

                <a
                  href={repoDetails.zipUrl}
                  download
                  className="py-2.5 px-3 rounded-xl bg-white/5 hover:bg-white/10 text-stone-300 hover:text-white font-medium text-xs flex items-center justify-center gap-1.5 transition-colors"
                  title={t.github.downloadZip}
                >
                  <Download className="w-3.5 h-3.5" />
                  <span>ZIP</span>
                </a>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-5 py-3 border-t border-white/5 bg-[#141413] flex items-center justify-between text-[11px] text-stone-500">
          <span>{lang === 'ar' ? 'يدعم الروابط العامة والخاصة' : 'Supports public & authenticated private repos'}</span>
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-stone-300 transition-colors"
          >
            {t.telemetry.close}
          </button>
        </div>
      </div>
    </div>
  );
};
