import React, { useEffect, useRef } from 'react';
import { Message, CodeArtifact } from '../types';
import { MessageItem } from './MessageItem';
import { Sparkles, Terminal, Shield, Zap } from 'lucide-react';
import { Language, translations } from '../i18n';

interface MessageListProps {
  messages: Message[];
  onOpenArtifact: (artifact: CodeArtifact) => void;
  onSelectPrompt: (prompt: string) => void;
  lang: Language;
}

export const MessageList: React.FC<MessageListProps> = ({
  messages,
  onOpenArtifact,
  onSelectPrompt,
  lang,
}) => {
  const bottomRef = useRef<HTMLDivElement>(null);
  const t = translations[lang];

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const promptIcons = [Terminal, Zap, Shield, Sparkles];

  return (
    <div id="messages-viewport" className="flex-1 overflow-y-auto px-4 sm:px-6 py-6">
      <div className="max-w-[760px] w-full mx-auto space-y-8">
        {messages.length === 0 ? (
          <div className="py-14 sm:py-20 space-y-6 text-center animate-fade-in" dir={lang === 'ar' ? 'rtl' : 'ltr'}>
            <div className="w-12 h-12 rounded-2xl bg-[#d97757]/15 border border-[#d97757]/30 flex items-center justify-center text-[#d97757] mx-auto text-2xl font-serif-anthropic font-bold shadow-lg shadow-[#d97757]/5">
              ✶
            </div>
            <div className="space-y-2.5 max-w-lg mx-auto">
              <h2 className="text-xl sm:text-2xl font-semibold text-stone-100 font-serif-anthropic tracking-tight">
                {t.welcome.title}
              </h2>
              <p className="text-xs sm:text-sm text-stone-400 leading-relaxed font-sans">
                {lang === 'ar'
                  ? 'المحادثة هي قلب المنظومة وواجهة التحكم الرئيسية. تحدث بكل طبيعية لإدارة المشاريع، ربط مستودعات GitHub، تدقيق الأكواد، أو فحص بيئة المضيف.'
                  : 'The chat is the core system controller. Speak naturally to manage projects, link GitHub repos, audit security, or synthesize production code.'}
              </p>
            </div>

            {/* Subtle, Clean Conversational Starters */}
            <div className="flex flex-wrap items-center justify-center gap-2 pt-2 max-w-xl mx-auto">
              {[
                {
                  text: lang === 'ar' ? 'انشئ مشروع جديد باسم Smart-Agent' : 'Create project named Smart-Agent',
                  icon: Terminal,
                },
                {
                  text: lang === 'ar' ? 'اربط مستودع github: facebook/react' : 'Connect repo facebook/react',
                  icon: Sparkles,
                },
                {
                  text: lang === 'ar' ? 'كيف حالة المضيف ROBEN وذاكرة الـ Vector؟' : 'Check ROBEN host status and vector memory',
                  icon: Zap,
                },
              ].map((item, idx) => {
                const Icon = item.icon;
                return (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => onSelectPrompt(item.text)}
                    className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/[0.03] hover:bg-white/[0.08] border border-white/10 hover:border-[#d97757]/40 text-stone-300 hover:text-white text-xs transition-all active:scale-95"
                  >
                    <Icon className="w-3.5 h-3.5 text-[#d97757]" />
                    <span>{item.text}</span>
                  </button>
                );
              })}
            </div>
          </div>
        ) : (
          messages.map((message) => (
            <MessageItem
              key={message.id}
              message={message}
              onOpenArtifact={onOpenArtifact}
              lang={lang}
            />
          ))
        )}

        <div ref={bottomRef} />
      </div>
    </div>
  );
};
