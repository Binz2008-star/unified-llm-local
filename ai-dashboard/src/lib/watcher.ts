/**
 * Code It - Intelligence Console / ROBEN AI OS
 * Phase 3.2 - Memory File Watcher
 * Watches memory/LESSONS.md and triggers ingest_memory on change (debounced).
 * Node native fs.watch, ESM, Node 22.
 */

import fs from 'fs';
import path from 'path';
import { ingestLessonsFile } from './ingest_memory.js';

export function watchLessons(targetPath = 'memory/LESSONS.md'): fs.FSWatcher {
  const candidates = [
    path.resolve(process.cwd(), targetPath),
    path.resolve(process.cwd(), '..', targetPath),
    path.resolve('X:/second-brain-kb', targetPath),
  ];
  let resolved = targetPath;
  for (const p of candidates) {
    try {
      fs.accessSync(p);
      resolved = p;
      break;
    } catch {}
  }
  console.log(`[Watcher] Watching ${resolved} for changes...`);

  let debounceTimer: NodeJS.Timeout | null = null;

  const watcher = fs.watch(resolved, (eventType) => {
    if (eventType === 'change') {
      if (debounceTimer) clearTimeout(debounceTimer);
      debounceTimer = setTimeout(async () => {
        console.log(`[Watcher] Change detected in ${targetPath}. Re-indexing...`);
        try {
          const n = await ingestLessonsFile(targetPath);
          console.log(`[Watcher] Re-indexing complete: ${n} chunks`);
        } catch (err) {
          console.error(`[Watcher] Re-indexing failed:`, err);
        }
      }, 1000);
    }
  });

  watcher.on('error', (err) => console.error(`[Watcher] watch error:`, err));
  return watcher;
}

// CLI: tsx ai-dashboard/src/lib/watcher.ts
if (import.meta.url === `file://${process.argv[1]?.replace(/\\/g, '/')}`) {
  watchLessons();
  console.log('[Watcher] Running — press Ctrl+C to stop');
}
