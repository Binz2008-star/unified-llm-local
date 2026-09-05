/**
 * Code It - Intelligence Console / ROBEN AI OS
 * Phase 3.3 - Memory Explorer Component
 * React 19, TypeScript, Tailwind CSS
 * Uses dedicated /api/phase3/memory list endpoint (no embedding for q=*)
 */

import React, { useEffect, useState } from 'react';

interface MemoryItem {
  id: number;
  lesson_id: string;
  source_file: string;
  content: string;
  tags: string[];
  created_at: string;
}

export function MemoryExplorer() {
  const [items, setItems] = useState<MemoryItem[]>([]);
  const [selected, setSelected] = useState<MemoryItem | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/phase3/memory?limit=20')
      .then((res) => res.json())
      .then((data) => {
        setItems(data.results || []);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  return (
    <div className="flex h-[600px] bg-slate-900 border border-slate-800 rounded-lg text-slate-100 overflow-hidden">
      <div className="w-1/3 border-r border-slate-800 overflow-y-auto p-3 space-y-2">
        <h3 className="font-semibold text-sm text-slate-400 mb-2">Ingested Lessons</h3>
        {loading ? (
          <div className="text-sm text-slate-500">Loading memory...</div>
        ) : (
          items.map((item) => (
            <div
              key={item.id}
              onClick={() => setSelected(item)}
              className={`p-2 rounded cursor-pointer text-sm truncate ${
                selected?.id === item.id ? 'bg-blue-600/30 border border-blue-500/50' : 'bg-slate-800/40 hover:bg-slate-800'
              }`}
            >
              <div className="font-mono text-xs text-blue-400">{item.lesson_id}</div>
              <div className="text-slate-300 truncate">{item.content.split('\n')[0]}</div>
            </div>
          ))
        )}
      </div>
      <div className="flex-1 p-4 overflow-y-auto">
        {selected ? (
          <div className="space-y-3">
            <div className="flex justify-between items-center border-b border-slate-800 pb-2">
              <span className="font-mono text-blue-400 font-semibold">{selected.lesson_id}</span>
              <span className="text-xs text-slate-500">{selected.source_file}</span>
            </div>
            <pre className="whitespace-pre-wrap font-mono text-xs bg-slate-950 p-3 rounded border border-slate-800 text-slate-300">
              {selected.content}
            </pre>
          </div>
        ) : (
          <div className="flex items-center justify-center h-full text-sm text-slate-500">
            Select a lesson to view full content
          </div>
        )}
      </div>
    </div>
  );
}
