/**
 * Code It - Intelligence Console / ROBEN AI OS
 * Phase 3.3 - Semantic Search Widget Component
 * React 19, TypeScript, Tailwind CSS
 */

import React, { useState } from 'react';

interface SearchResult {
  id: number | string;
  lesson_id?: string;
  source_file?: string;
  content: string;
  tags?: string[];
  similarity?: number;
  rank?: number;
}

export function SearchWidget() {
  const [query, setQuery] = useState('');
  const [mode, setMode] = useState<'hybrid' | 'memory'>('hybrid');
  const [topK, setTopK] = useState(5);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setError(null);

    try {
      const res = await fetch('/api/phase3/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, mode, topK }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.error || `Search failed with status ${res.status}`);
      }

      const data = await res.json();
      setResults(data.results || []);
    } catch (err: any) {
      setError(err.message || 'An error occurred during search.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-4 bg-slate-900 border border-slate-800 rounded-lg text-slate-100 max-w-2xl mx-auto">
      <h2 className="text-lg font-semibold mb-4">Vector Memory & Hybrid Search</h2>
      <form onSubmit={handleSearch} className="space-y-3">
        <div>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search lessons or codebase chunks..."
            className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div className="flex gap-4 items-center text-sm">
          <label className="flex items-center gap-1">
            Mode:
            <select
              value={mode}
              onChange={(e) => setMode(e.target.value as 'hybrid' | 'memory')}
              className="bg-slate-800 border border-slate-700 rounded px-2 py-1"
            >
              <option value="hybrid">Hybrid RRF</option>
              <option value="memory">Memory Vector Only</option>
            </select>
          </label>
          <label className="flex items-center gap-1">
            Top K:
            <input
              type="number"
              value={topK}
              onChange={(e) => setTopK(parseInt(e.target.value) || 5)}
              min={1}
              max={20}
              className="w-16 bg-slate-800 border border-slate-700 rounded px-2 py-1"
            />
          </label>
          <button
            type="submit"
            disabled={loading}
            className="ml-auto px-4 py-1.5 bg-blue-600 hover:bg-blue-500 rounded font-medium disabled:opacity-50"
          >
            {loading ? 'Searching...' : 'Search'}
          </button>
        </div>
      </form>

      {error && <div className="mt-4 p-3 bg-red-900/50 border border-red-700 rounded text-red-200 text-sm">{error}</div>}

      <div className="mt-6 space-y-3">
        {results.map((r, i) => (
          <div key={r.id || i} className="p-3 bg-slate-800/60 border border-slate-700/60 rounded text-sm space-y-1">
            <div className="flex justify-between items-center text-xs text-slate-400">
              <span className="font-mono text-blue-400">{r.lesson_id || `Item #${r.id}`}</span>
              {r.similarity !== undefined && <span>Score: {r.similarity.toFixed(3)}</span>}
            </div>
            <p className="whitespace-pre-wrap font-sans text-slate-200">{r.content}</p>
            {r.tags && r.tags.length > 0 && (
              <div className="flex gap-1 pt-1">
                {r.tags.map((t) => (
                  <span key={t} className="px-1.5 py-0.5 bg-slate-700 text-xs rounded text-slate-300">
                    {t}
                  </span>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
