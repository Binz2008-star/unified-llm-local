"""
Evolve - Self-evolution engine
Agent analyzes its own failures and improves its tools/code
"""
import asyncio
import hashlib
import os
import re
from pathlib import Path
from datetime import datetime
from typing import Optional
import asyncpg
from dotenv import load_dotenv
import aiohttp

ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env")

DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("NEON_DSN")
OLLAMA_EMBED_URL = os.getenv("OLLAMA_EMBED_URL", "http://127.0.0.1:11434/api/embed")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
# Durable-state AGENTS.md is what OpenCode loads into context each session.
AGENTS_MD = Path(os.getenv("SECOND_BRAIN_AGENTS_MD", str(Path(__file__).parent / "AGENTS.md")))

class Evolver:
    def __init__(self):
        self.root = ROOT
        self.memory_dir = self.root / "memory"
        self.memory_dir.mkdir(exist_ok=True)
        self._pool = None
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self):
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=180, connect=30)
            )
        return self._session

    async def get_pool(self):
        if self._pool is None:
            self._pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=4, command_timeout=120)
        return self._pool

    async def embed(self, text: str):
        """Generate embedding for text using shared aiohttp session"""
        if not text or not text.strip():
            return [0.0] * 768
        session = await self._get_session()
        for _ in range(3):
            try:
                async with session.post(OLLAMA_EMBED_URL, json={"model": EMBED_MODEL, "input": text}) as r:
                    j = await r.json()
                    return j["embeddings"][0]
            except Exception:
                await asyncio.sleep(1)
        raise RuntimeError("embed failed")

    async def analyze_failures(self):
        """Analyze recent conversations for failures"""
        try:
            pool = await self.get_pool()
            async with pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT content FROM conversations
                    WHERE content ~* '(❌|\\bFAILED\\b|Traceback \\(most recent call last\\)|\\bError:\\s|\\bException:\\s|\\bfailed to\\b|\\btimed out\\b|RuntimeError:|ValueError:|TypeError:|ImportError:|ModuleNotFoundError:|ConnectionError:|TimeoutError:)'
                    ORDER BY created_at DESC LIMIT 20
                """)
            return [r["content"] for r in rows]
        except Exception:
            return []

    async def evolve_chunker(self):
        """Improve chunker based on search quality"""
        try:
            pool = await self.get_pool()
            async with pool.acquire() as conn:
                low_score = await conn.fetchval("""
                    SELECT COUNT(*) FROM conversations
                    WHERE content LIKE '%score=0.2%' OR content LIKE '%No results%' OR content LIKE '%no relevant%'
                """)
            if low_score and low_score > 5:
                print(f"⚠️  Detected {low_score} low-score searches - chunker may need improvement")
                return "Consider reducing chunk_size to 800, improving AST chunker for better boundaries"
        except Exception:
            pass
        return None

    async def evolve_tools(self):
        """Check which tools fail most and improve them"""
        failures = await self.analyze_failures()
        if not failures:
            print("✅ No failures detected - system healthy")
            return

        print(f"🔍 Found {len(failures)} failures to analyze")
        fixes = []
        for f in failures:
            if "File not found" in f or "No such file" in f:
                fixes.append("Improve path resolution - add more fallback paths for project roots")
            if "embedding" in f.lower() and "vector" in f.lower():
                fixes.append("Vector dimension mismatch - check EMBED_DIM consistency across stores")
            if "timeout" in f.lower() or "timed out" in f.lower():
                fixes.append("Increase shell/chat timeout, add retry with backoff")

        if fixes:
            lessons_path = self.memory_dir / "LESSONS.md"
            unique_fixes = list(set(fixes))
            with open(lessons_path, 'a', encoding='utf-8') as fh:
                fh.write(f"\n## {datetime.now()} - Auto-evolution\n")
                for fix in unique_fixes:
                    fh.write(f"- {fix}\n")
            print(f"📝 Added {len(unique_fixes)} lessons to {lessons_path}")
            
            # Auto-embed lessons for searchable memory
            print("🔮 Embedding lessons for searchable memory...")
            pool = await self.get_pool()
            for fix in unique_fixes:
                try:
                    emb = await self.embed(fix)
                    emb_str = "[" + ",".join(f"{x:.6f}" for x in emb) + "]"
                    # Stable, deterministic lesson_id so re-runs upsert instead of duplicating
                    lesson_id = f"{datetime.now():%Y-%m-%d-%H%M}-{hashlib.md5(fix.encode()).hexdigest()[:10]}"
                    tags = ["auto", "failure", "lesson"]
                    async with pool.acquire() as conn:
                        await conn.execute("""
                            INSERT INTO memory
                                (lesson_id, source_file, content, embedding, tags, type, project_id, linked_chunk_id)
                            VALUES ($1, $2, $3, $4::vector, $5, 'lesson', $6, NULL)
                            ON CONFLICT (lesson_id) DO UPDATE SET
                                content = EXCLUDED.content,
                                embedding = EXCLUDED.embedding,
                                tags = EXCLUDED.tags
                        """, lesson_id, "memory/LESSONS.md", fix, emb_str, tags, "second-brain")
                    print(f"   ✓ Embedded: {fix[:60]}... (lesson_id={lesson_id})")
                except Exception as e:
                    print(f"   ⚠️ Failed to embed lesson: {e}")

    async def generate_improvements(self):
        """Use LLM to suggest code improvements based on failure analysis"""
        failures = await self.analyze_failures()
        if not failures:
            print("✅ No failures detected, using default improvement list")
            improvements = [
                "Chunk TypeScript/JavaScript ASTs (currently Python only) for better symbol boundaries",
                "Add streaming for agent tool calls in the Web UI",
                "Auto-commit after successful task with conventional commit message",
                "Add file watcher for MEMORY.md auto-reload",
            ]
        else:
            failure_text = "\n".join(failures[:10])
            prompt = f"""Analyze these failure patterns from conversation history and suggest 4-6 concrete improvements:

{failure_text}

Return ONLY a numbered list of improvements, one per line. Focus on:
1. Code quality improvements
2. Tool reliability fixes
3. Performance optimizations
4. New features needed

Do NOT include markdown formatting, code blocks, or explanations."""
            try:
                session = await self._get_session()
                async with session.post(OLLAMA_EMBED_URL.replace("/api/embed", "/api/chat"), json={
                    "model": EMBED_MODEL,
                    "messages": [{"role": "system", "content": "You are an evolution analyst. Return only a numbered list of improvements."}, {"role": "user", "content": prompt}],
                    "stream": False
                }, timeout=aiohttp.ClientTimeout(total=60)) as r:
                    data = await r.json()
                    content = data.get("message", {}).get("content", "")
                    improvements = [line.strip().lstrip("0123456789. -") for line in content.strip().split("\n") if line.strip()]
                    if not improvements:
                        improvements = ["Add streaming for agent tool calls in the Web UI"]
            except Exception as e:
                print(f"⚠️ LLM improvement generation failed: {e}")
                improvements = ["Add streaming for agent tool calls in the Web UI"]

        todo_path = self.root / "EVOLVE_TODO.md"
        with open(todo_path, 'w', encoding='utf-8') as f:
            f.write(f"# Evolution TODO - {datetime.now()}\n\n")
            for imp in improvements:
                f.write(f"- [ ] {imp}\n")

        print(f"📋 Generated evolution TODOs: {todo_path}")
        return improvements

    def apply_proposals(self, improvements):
        """Auto-apply proposals into the durable-state 'Not done / next' list.

        Idempotent (skips text already present) and non-destructive (only ever
        appends to that list, never rewrites existing lines). Failures fail soft.
        """
        if not AGENTS_MD.exists():
            print(f"   ⚠️ Auto-apply skipped: {AGENTS_MD} not found")
            return 0
        # Fallback: derive proposals from EVOLVE_TODO.md's unchecked items when the
        # caller supplies none. Guarded by `imp not in text` below to stay idempotent.
        if not improvements and (self.root / "EVOLVE_TODO.md").exists():
            try:
                todo_text = (self.root / "EVOLVE_TODO.md").read_text(encoding="utf-8")
                improvements = [
                    m.group(1) for m in re.finditer(r"^- \[ \] (.+)", todo_text, re.M)
                ]
            except Exception as e:
                print(f"   ⚠️ Could not read EVOLVE_TODO.md for fallback: {e}")
                improvements = []
        text = AGENTS_MD.read_text(encoding="utf-8")
        added = [imp for imp in improvements if imp not in text]
        if not added:
            print("   ✓ No new proposals — AGENTS.md already current")
            return 0
        anchor = "### Not done / next"
        start = text.find(anchor)
        if start == -1:
            print(f"   ⚠️ Auto-apply skipped: '{anchor}' block not found in {AGENTS_MD.name}")
            return 0
        # Insert just before the next heading after the anchor block.
        tail = text[start:]
        m = re.search(r"\n#{2,3} ", tail)
        end = start + m.start() + 1 if m else len(text)
        insertion = "".join(f"- {imp}\n" for imp in added) + "\n"
        AGENTS_MD.write_text(text[:end] + insertion + text[end:], encoding="utf-8")
        print(f"   ✓ Auto-applied {len(added)} proposal(s) to {AGENTS_MD.name}")
        return len(added)


async def evolve():
    print("🧬 Starting self-evolution...\n")
    ev = Evolver()

    print("1. Analyzing failures...")
    await ev.evolve_tools()

    print("\n2. Checking chunker quality...")
    suggestion = await ev.evolve_chunker()
    if suggestion:
        print(f"   Suggestion: {suggestion}")

    print("\n3. Generating improvements...")
    imps = await ev.generate_improvements()
    for imp in imps:
        print(f"   - {imp}")

    print("\n4. Auto-applying proposals to AGENTS.md (durable state)...")
    ev.apply_proposals(imps)

    print("\n✅ Evolution complete. Check memory/LESSONS.md, EVOLVE_TODO.md, AGENTS.md")
    if ev._pool:
        await ev._pool.close()
    if ev._session and not ev._session.closed:
        await ev._session.close()


if __name__ == "__main__":
    asyncio.run(evolve())