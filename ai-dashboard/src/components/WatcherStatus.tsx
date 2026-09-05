/**
 * Code It - Intelligence Console / ROBEN AI OS
 * Phase 3.3 - Watcher Status Telemetry
 * Polls GET /api/phase3/watcher/status, shows watching/lastIndexed/chunks
 */

import React, { useEffect, useState } from 'react';

interface WatcherStatusData {
  watching: boolean;
  lastIndexed: string | null;
  count: number;
  source_file: string;
}

export function WatcherStatus() {
  const [data, setData] = useState<WatcherStatusData | null>(null);

  useEffect(() => {
    let cancelled = false;
    const fetchStatus = async () => {
      try {
        const res = await fetch('/api/phase3/watcher/status');
        const j = await res.json();
        if (!cancelled) setData(j);
      } catch {
        // ignore
      }
    };
    fetchStatus();
    const id = setInterval(fetchStatus, 10000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  if (!data) return null;

  return (
    <div className="flex items-center gap-2 text-xs font-mono">
      <span
        className={`w-2 h-2 rounded-full ${data.watching ? 'bg-emerald-400 shadow-[0_0_6px_#34d399]' : 'bg-slate-500'}`}
        title={data.watching ? 'Watching memory/LESSONS.md' : 'Idle'}
      />
      <span className={data.watching ? 'text-emerald-300' : 'text-slate-400'}>
        {data.watching ? 'Watching' : 'Idle'}
      </span>
      <span className="text-slate-500">·</span>
      <span className="text-slate-400">{data.count} lessons</span>
      {data.lastIndexed && (
        <>
          <span className="text-slate-500">·</span>
          <span className="text-slate-500">last {new Date(data.lastIndexed).toLocaleTimeString()}</span>
        </>
      )}
    </div>
  );
}
