"""
Memory Manager - Long-term evolving memory
Learns from conversations, stores patterns, lessons, preferences

Files:
- MEMORY.md - Who user is, preferences
- PATTERNS.md - Code patterns across repos
- LESSONS.md - What went wrong, what works
- CONTEXT.md - Current project context
"""
import os
import json
import asyncio
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Callable
import asyncpg

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False

# Shared observer instance to prevent leaks
_shared_observer = None

class MemoryManager:
    def __init__(self, pool: asyncpg.Pool = None, memory_dir: str = "./memory", on_reload: Callable = None):
        self.pool = pool
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(exist_ok=True)
        self.on_reload = on_reload

        # Memory files
        self.files = {
            "memory": self.memory_dir / "MEMORY.md",
            "patterns": self.memory_dir / "PATTERNS.md",
            "lessons": self.memory_dir / "LESSONS.md",
            "context": self.memory_dir / "CONTEXT.md",
        }

        # Ensure files exist
        for name, path in self.files.items():
            if not path.exists():
                path.write_text(f"# {name.upper()}\n\nAuto-generated {datetime.now()}\n\n", encoding='utf-8')

        # Start file watcher
        self._start_watcher()

    def _start_watcher(self):
        """Start watching memory files for changes"""
        global _shared_observer
        if not WATCHDOG_AVAILABLE:
            return

        if _shared_observer is None:
            class MemoryFileHandler(FileSystemEventHandler):
                def __init__(self, manager):
                    self.manager = manager
                    self._debounce = {}

                def on_modified(self, event):
                    if event.is_directory:
                        return
                    path = Path(event.src_path)
                    # Debounce rapid writes
                    now = time.time()
                    if path in self._debounce and now - self._debounce[path] < 0.5:
                        return
                    self._debounce[path] = now

                    # Check if it's one of our memory files
                    for name, fpath in self.manager.files.items():
                        try:
                            if path.samefile(fpath):
                                print(f"[Memory] Detected change in {name}, reloading...")
                                if self.manager.on_reload:
                                    self.manager.on_reload(name, fpath)
                                break
                        except OSError:
                            pass

            handler = MemoryFileHandler(self)
            _shared_observer = Observer()
            _shared_observer.schedule(handler, str(self.memory_dir), recursive=False)
            _shared_observer.start()
            print(f"[Memory] File watcher started on {self.memory_dir}")
        else:
            print(f"[Memory] Using shared file watcher")

    def stop_watcher(self):
        """Stop the file watcher"""
        global _shared_observer
        # Only stop if we're the last instance (simplified - just don't stop shared)
        # The observer will be stopped at process exit
        pass

    async def add_memory(self, type: str, content: str, project_id: str = None, embedding=None):
        """Add to both file and Neon"""
        # Add to file
        file_key = {"pattern": "patterns", "lesson": "lessons", "fact": "memory", "preference": "memory"}.get(type, "memory")
        path = self.files[file_key]

        entry = f"\n## {datetime.now().strftime('%Y-%m-%d %H:%M')} [{type}] {project_id or ''}\n{content}\n"
        with open(path, 'a', encoding='utf-8') as f:
            f.write(entry)

        # Add to Neon with embedding
        if embedding and self.pool is not None:
            emb_str = "[" + ",".join(f"{x:.6f}" for x in embedding) + "]"
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO memory (type, content, project_id, embedding)
                    VALUES ($1, $2, $3, $4::vector)
                """, type, content, project_id, emb_str)

    async def search_memory(self, query_embedding, top_k=5):
        """Search long-term memory"""
        if self.pool is None:
            return []
        emb_str = "[" + ",".join(f"{x:.6f}" for x in query_embedding) + "]"
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT type, content, project_id, 1 - (embedding <=> $1::vector) as sim
                FROM memory
                ORDER BY embedding <=> $1::vector
                LIMIT $2
            """, emb_str, top_k)
            return rows

    def get_context(self) -> str:
        """Get current full context for agent prompt"""
        ctx = ""
        for name, path in self.files.items():
            if path.exists():
                content = path.read_text(encoding='utf-8')[-3000:]  # last 3k chars
                ctx += f"\n--- {name.upper()} ---\n{content}\n"
        return ctx

    def auto_learn_from_conversation(self, user_msg: str, assistant_msg: str, tool_results: List[str]):
        """Extract lessons automatically"""
        # Simple heuristics - can be replaced with LLM extraction later
        lessons = []

        # If tool failed, learn
        for res in tool_results:
            if "❌" in res or "Error" in res:
                lessons.append(f"Tool failed: {res[:200]} when user asked: {user_msg[:100]}")

        # If user corrected, learn preference
        if any(w in user_msg.lower() for w in ["actually", "no, ", "should be", "prefer"]):
            lessons.append(f"User preference: {user_msg}")

        return lessons

# Auto-updating AGENT instructions that evolve
EVOLVING_AGENT_MD = """# Second Brain Agent - Evolving Instructions

You are a SOTA autonomous coding agent with perfect memory.

## Current Context (auto-updated)
{context}

## Projects
{projects}

## Learned Patterns
{patterns}

## Lessons
{lessons}

## Rules (evolve these as you learn):
1. ALWAYS search_brain first before answering about code
2. Switch project when task mentions different repo
3. Create small diffs, test after
4. Update MEMORY.md when you learn user preference
5. If tool fails 2x, try alternative approach
6. Ask before deleting files (unless user said delete)
7. Commit with conventional commits: feat:, fix:, docs:

## Self-Evolution
- After each task, reflect: what worked, what didn't?
- If you notice repeated pattern, add to PATTERNS.md
- If you fail, add to LESSONS.md
- You can rewrite your own tools in brain-agent-v4.py if needed (self-evolution)

Last updated: {timestamp}
"""
