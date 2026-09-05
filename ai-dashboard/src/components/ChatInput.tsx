import React, { useRef, useState } from 'react';
import { Paperclip, Send, X, FileCode, Loader2, Sparkles, MessageSquare, Terminal, Shield, FileText } from 'lucide-react';
import { AttachedFile } from '../types';
import { Language, translations } from '../i18n';

interface ChatInputProps {
  onSendMessage: (text: string, files: AttachedFile[]) => void;
  isGenerating: boolean;
  initialText?: string;
  onTextChange?: (text: string) => void;
  lang: Language;
  onTriggerAiAction?: (action: 'summarize' | 'natural_chat' | 'code_gen' | 'audit') => void;
  showQuickChips?: boolean;
}

export const ChatInput: React.FC<ChatInputProps> = ({
  onSendMessage,
  isGenerating,
  initialText = '',
  onTextChange,
  lang,
  onTriggerAiAction,
  showQuickChips = true,
}) => {
  const [text, setText] = useState(initialText);
  const [attachedFiles, setAttachedFiles] = useState<AttachedFile[]>([]);
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const t = translations[lang];

  // Synchronize when initialText changes
  React.useEffect(() => {
    if (initialText !== undefined && initialText !== text) {
      setText(initialText);
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
        textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 180)}px`;
      }
    }
  }, [initialText]);

  const handleTextChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const val = e.target.value;
    setText(val);
    if (onTextChange) onTextChange(val);

    // Auto-grow
    e.target.style.height = 'auto';
    e.target.style.height = `${Math.min(e.target.scrollHeight, 180)}px`;
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleSend = () => {
    const trimmed = text.trim();
    if ((!trimmed && attachedFiles.length === 0) || isGenerating) return;

    onSendMessage(trimmed, attachedFiles);
    setText('');
    setAttachedFiles([]);
    if (onTextChange) onTextChange('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const readFileContent = (file: File): Promise<string> => {
    return new Promise((resolve) => {
      const reader = new FileReader();
      reader.onload = () => {
        resolve((reader.result as string) || '');
      };
      reader.onerror = () => resolve('');
      reader.readAsText(file);
    });
  };

  const handleFiles = async (files: FileList | null) => {
    if (!files) return;
    const newFiles: AttachedFile[] = [];

    for (let i = 0; i < files.length; i++) {
      const f = files[i];
      if (!attachedFiles.some((existing) => existing.name === f.name && existing.size === f.size)) {
        const content = await readFileContent(f);
        newFiles.push({
          name: f.name,
          size: f.size,
          type: f.type,
          content,
        });
      }
    }

    setAttachedFiles((prev) => [...prev, ...newFiles]);
  };

  const removeFile = (index: number) => {
    setAttachedFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleChipClick = (action: 'summarize' | 'natural_chat' | 'code_gen' | 'audit') => {
    if (action === 'summarize') {
      if (onTriggerAiAction) {
        onTriggerAiAction('summarize');
      } else {
        onSendMessage(
          lang === 'ar'
            ? 'قم بتلخيص هذه الجلسة الهندسية وتوضيح أهم القرارات والأكواد المنفذة.'
            : 'Please summarize this engineering session, key decisions made, and next steps.',
          []
        );
      }
    } else if (action === 'natural_chat') {
      const prompt = lang === 'ar' ? 'ما رأيك في معمارية هذا المشروع وما هي أفضل الممارسات الموصى بها؟' : 'What are your architectural thoughts on this project structure and recommended patterns?';
      setText(prompt);
      if (onTextChange) onTextChange(prompt);
      textareaRef.current?.focus();
    } else if (action === 'code_gen') {
      const prompt = lang === 'ar' ? 'قم ببرمجة وحدة خدمة متكاملة مع معالجة الأخطاء والتوثيق لمشروعي الحالي.' : 'Please write a production-ready module with error handling and full documentation for the active project.';
      setText(prompt);
      if (onTextChange) onTextChange(prompt);
      textareaRef.current?.focus();
    } else if (action === 'audit') {
      const prompt = lang === 'ar' ? 'قم بإجراء فحص أمني وتدقيق للثغرات والتحقق من المدخلات ومعدل الطلبات.' : 'Perform a comprehensive security audit for vulnerabilities, input sanitization, and rate-limiting.';
      setText(prompt);
      if (onTextChange) onTextChange(prompt);
      textareaRef.current?.focus();
    }
  };

  return (
    <div className="max-w-[760px] w-full mx-auto px-4 pb-3 sm:pb-4 shrink-0 safe-bottom">
      {/* Quick AI Capabilities & Intent Chips */}
      {showQuickChips && (
        <div className="flex items-center gap-1.5 pb-2 overflow-x-auto no-scrollbar text-xs animate-fade-in" dir={lang === 'ar' ? 'rtl' : 'ltr'}>
          <span className="text-[10px] font-mono text-[#d97757] uppercase tracking-wider shrink-0 flex items-center gap-1 px-1">
            <Sparkles className="w-3 h-3 text-[#d97757]" />
            <span>AI:</span>
          </span>

          <button
            type="button"
            onClick={() => handleChipClick('natural_chat')}
            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-white/[0.03] hover:bg-white/[0.08] border border-white/5 text-stone-300 text-[11px] whitespace-nowrap transition-colors active:scale-95"
            title={t.aiActions.naturalChat}
          >
            <MessageSquare className="w-3 h-3 text-cyan-400" />
            <span>{t.aiActions.naturalChat}</span>
          </button>

          <button
            type="button"
            onClick={() => handleChipClick('code_gen')}
            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-white/[0.03] hover:bg-white/[0.08] border border-white/5 text-stone-300 text-[11px] whitespace-nowrap transition-colors active:scale-95"
            title={t.aiActions.codeGen}
          >
            <Terminal className="w-3 h-3 text-[#d97757]" />
            <span>{t.aiActions.codeGen}</span>
          </button>

          <button
            type="button"
            onClick={() => handleChipClick('summarize')}
            disabled={isGenerating}
            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-white/[0.03] hover:bg-white/[0.08] border border-white/5 text-stone-300 text-[11px] whitespace-nowrap transition-colors active:scale-95 disabled:opacity-50"
            title={t.aiActions.summarize}
          >
            <FileText className="w-3 h-3 text-amber-400" />
            <span>{t.aiActions.summarize}</span>
          </button>

          <button
            type="button"
            onClick={() => handleChipClick('audit')}
            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-white/[0.03] hover:bg-white/[0.08] border border-white/5 text-stone-300 text-[11px] whitespace-nowrap transition-colors active:scale-95"
            title={t.aiActions.audit}
          >
            <Shield className="w-3 h-3 text-emerald-400" />
            <span>{t.aiActions.audit}</span>
          </button>
        </div>
      )}

      <div
        id="input-dock"
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragOver(true);
        }}
        onDragLeave={() => setIsDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setIsDragOver(false);
          handleFiles(e.dataTransfer.files);
        }}
        className={`bg-[#1e1e1c] border rounded-2xl p-3 shadow-xl transition-all ${
          isDragOver
            ? 'border-[#d97757] shadow-[0_0_20px_rgba(217,119,87,0.25)]'
            : 'border-white/[0.08] hover:border-white/[0.14]'
        }`}
      >
        {/* Attached Files List */}
        {attachedFiles.length > 0 && (
          <div className="flex flex-wrap gap-2 pb-2.5 mb-1.5 border-b border-white/5">
            {attachedFiles.map((file, idx) => (
              <div
                key={idx}
                className="flex items-center gap-1.5 bg-white/5 border border-white/10 text-stone-300 px-2.5 py-1 rounded-lg text-xs font-mono-code"
              >
                <FileCode className="w-3.5 h-3.5 text-[#d97757]" />
                <span className="truncate max-w-[130px]">{file.name}</span>
                <span className="text-[10px] text-stone-500">
                  {Math.round(file.size / 1024)}K
                </span>
                <button
                  onClick={() => removeFile(idx)}
                  className="text-stone-500 hover:text-stone-200 ml-1 p-0.5 rounded hover:bg-white/10"
                  title={t.input.removeFile}
                >
                  <X className="w-3 h-3" />
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Text Input */}
        <textarea
          ref={textareaRef}
          id="task-input"
          value={text}
          onChange={handleTextChange}
          onKeyDown={handleKeyDown}
          rows={1}
          placeholder={t.input.placeholder}
          className="w-full bg-transparent border-none outline-none resize-none text-stone-100 text-[14.5px] leading-relaxed placeholder:text-stone-500 max-h-[180px]"
          dir={lang === 'ar' ? 'rtl' : 'ltr'}
        />

        <input
          ref={fileInputRef}
          type="file"
          multiple
          className="hidden"
          onChange={(e) => handleFiles(e.target.files)}
        />

        {/* Dock Controls */}
        <div className="flex items-center justify-between pt-2 border-t border-white/[0.05] mt-1">
          <div className="flex items-center gap-2">
            <button
              type="button"
              id="attach-file-btn"
              onClick={() => fileInputRef.current?.click()}
              className="min-h-[38px] px-2.5 py-1.5 text-stone-400 hover:text-stone-200 hover:bg-white/5 rounded-lg transition-colors flex items-center gap-1.5 text-xs active:scale-95"
              title={t.input.attach}
            >
              <Paperclip className="w-4 h-4" />
              <span className="hidden sm:inline text-[11px] text-stone-400">{t.input.attach}</span>
            </button>

            {attachedFiles.length > 0 && (
              <span className="text-[11px] text-[#d97757] font-mono-code">
                {attachedFiles.length} {t.input.attachments}
              </span>
            )}
          </div>

          <button
            id="send-btn"
            onClick={handleSend}
            disabled={(!text.trim() && attachedFiles.length === 0) || isGenerating}
            className={`min-h-[38px] inline-flex items-center gap-1.5 px-4 py-1.5 rounded-xl text-xs font-medium text-white transition-all active:scale-95 ${
              (!text.trim() && attachedFiles.length === 0) || isGenerating
                ? 'bg-stone-700 text-stone-400 opacity-60 cursor-not-allowed'
                : 'bg-[#d97757] hover:bg-[#c26648] shadow-md shadow-[#d97757]/20 cursor-pointer'
            }`}
          >
            {isGenerating ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>{t.input.generating}</span>
              </>
            ) : (
              <>
                <span>{t.input.send}</span>
                <Send className="w-3.5 h-3.5 rtl:rotate-180" />
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
