/**
 * Code It - Intelligence Console / ROBEN AI OS Dashboard
 * CodeReviewView.tsx - AI-Powered Static Analysis & Scoring
 *
 * Author: Second Brain KB Team
 * License: MIT
 */

import { useState } from "react";
import { useApp } from "../context/AppContext";

export default function CodeReviewView() {
    const { sendPrompt, isProcessing, addNotification } = useApp();
    const [code, setCode] = useState("");
    const [analysis, setAnalysis] = useState<string | null>(null);

    const handleReview = async () => {
        if (!code.trim()) {
            addNotification({
                id: Date.now().toString(),
                type: "warning",
                title: "Empty Input",
                message: "Please paste some code to review.",
            });
            return;
        }

        // تجهيز الطلب ليقوم الذكاء الاصطناعي بمراجعة الكود
        const prompt = `Please perform a rigorous code review on the following code. Provide:
1. A quality score out of 10.
2. Potential bugs or logical errors.
3. Performance optimization suggestions.
4. Security vulnerabilities (if any).
5. Clean code & architecture advice.

Code to review:
\`\`\`
${code}
\`\`\``;

        const result = await sendPrompt(prompt);
        if (result) {
            setAnalysis(result);
            addNotification({
                id: Date.now().toString(),
                type: "success",
                title: "Review Complete",
                message: "AI static analysis finished successfully.",
            });
        } else {
            addNotification({
                id: Date.now().toString(),
                type: "error",
                title: "Analysis Failed",
                message: "Backend unreachable or request timed out.",
            });
        }
    };

    return (
        <div className="flex flex-col lg:flex-row gap-6 h-full min-h-[500px]" dir="ltr">
            {/* Input Section */}
            <div className="flex-1 flex flex-col bg-white/5 border border-white/10 rounded-xl overflow-hidden shadow-lg">
                <div className="px-4 py-3 bg-black/40 border-b border-white/10 flex justify-between items-center">
                    <h3 className="text-sm font-bold text-cyan-200 font-mono flex items-center gap-2">
                        <span>📝</span> SOURCE CODE
                    </h3>
                    <button
                        onClick={handleReview}
                        disabled={isProcessing || !code.trim()}
                        className="px-4 py-1.5 bg-gradient-to-r from-cyan-600 to-violet-600 hover:from-cyan-500 hover:to-violet-500 text-white rounded-lg text-xs font-semibold disabled:opacity-50 transition-all font-mono shadow-md"
                    >
                        {isProcessing ? "Analyzing..." : "Run Analysis"}
                    </button>
                </div>
                <textarea
                    value={code}
                    onChange={(e) => setCode(e.target.value)}
                    placeholder="Paste your TypeScript, Python, or React code here..."
                    className="flex-1 w-full bg-[#0a0f1c]/50 text-sm text-gray-300 font-mono p-4 outline-none resize-none placeholder-gray-600 focus:bg-[#0a0f1c]/80 transition-colors"
                    spellCheck={false}
                />
            </div>

            {/* Results Section */}
            <div className="flex-1 flex flex-col bg-white/5 border border-white/10 rounded-xl overflow-hidden shadow-lg">
                <div className="px-4 py-3 bg-black/40 border-b border-white/10">
                    <h3 className="text-sm font-bold text-cyan-200 font-mono flex items-center gap-2">
                        <span>🔍</span> AI ANALYSIS & SCORING
                    </h3>
                </div>
                <div className="flex-1 overflow-y-auto p-4 text-sm font-mono whitespace-pre-wrap text-gray-300 bg-[#0a0f1c]/30">
                    {isProcessing ? (
                        <div className="flex flex-col items-center justify-center h-full space-y-4">
                            <div className="animate-spin w-8 h-8 border-2 border-cyan-500/50 border-t-cyan-400 rounded-full" />
                            <p className="text-cyan-400/80 animate-pulse text-xs tracking-widest">RUNNING DEEP STATIC ANALYSIS...</p>
                        </div>
                    ) : analysis ? (
                        <div className="prose prose-invert prose-sm max-w-none prose-pre:bg-black/50 prose-pre:border prose-pre:border-white/10">
                            {analysis}
                        </div>
                    ) : (
                        <div className="flex flex-col items-center justify-center h-full text-gray-600 space-y-3">
                            <span className="text-4xl opacity-50">🤖</span>
                            <p className="text-xs tracking-wider">Awaiting code input to begin review.</p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
