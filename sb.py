#!/usr/bin/env python3
"""
sb - Unified CLI - ONE command does all (like opencode)
Usage:
  sb chat                    # Q&A (interactive)
  sb agent "task"            # Full multi-agent autonomous
  sb search "query"          # Search brain
  sb status                  # Health check
  sb evolve                  # Self-improve
  sb switch <project>        # Switch repo
  sb ui                      # Start web UI + API
"""
import sys
import os
from pathlib import Path
import subprocess
import argparse
import asyncio

ROOT = Path(__file__).parent
KB_ROOT = ROOT

# Load .env from KB root
try:
    from dotenv import load_dotenv
    load_dotenv(KB_ROOT / ".env")
except Exception as e:
    print(f"[dotenv] {e}")


def run(cmd, **kwargs):
    print(f"$ {cmd}")
    return subprocess.run(cmd, shell=True, **kwargs)


def _env_project_path(project_id: str) -> str | None:
    import brain_agent_v4 as ba
    p = ba.PROJECTS.get(project_id)
    return str(p) if p else os.getenv(f"PROJECT_{project_id.upper().replace('-', '_')}") or os.getenv(f"PROJECT_{project_id.upper()}")


def cmd_chat(args):
    from brain_agent_v4 import interactive_v4
    asyncio.run(interactive_v4())


def cmd_agent(args):
    from brain_agent_v4 import run_multi_agent
    task = " ".join(args.task) if args.task else args.prompt
    if not task:
        task = input("Task: ")
    asyncio.run(run_multi_agent(task))


def cmd_search(args):
    from brain_agent_v4 import search_brain
    query = " ".join(args.query)
    async def do_search():
        results = await search_brain(query, top_k=args.top_k)
        for i, r in enumerate(results, 1):
            print(f"\n{i}. [{r['project_id']}/{r['file_path']}] sim={float(r.get('similarity', 0)):.3f}")
            print(f"   {r.get('chunk_name')}")
            print(f"   {r['content'][:500]}")
    asyncio.run(do_search())


def cmd_status(args):
    print("🔍 Checking Second Brain v4 status...\n")

    print("🤖 Ollama models:")
    run("ollama list")

    print("\n📡 Neon DB:")
    try:
        import asyncpg
        from dotenv import load_dotenv
        load_dotenv(KB_ROOT / ".env")
        DSN = os.getenv("NEON_DSN")
        async def check():
            conn = await asyncpg.connect(DSN, timeout=30)
            try:
                for tbl in ["chunks", "chunks_v4", "memory", "conversations"]:
                    try:
                        cnt = await conn.fetchval(f"SELECT COUNT(*) FROM {tbl}")
                        print(f"  {tbl}: {cnt}")
                    except Exception:
                        print(f"  {tbl}: n/a")
                try:
                    edges = await conn.fetchval("SELECT COUNT(*) FROM code_graph")
                    print(f"  code_graph: {edges}")
                except Exception:
                    print(f"  code_graph: n/a")
            finally:
                await conn.close()
        asyncio.run(check())
    except Exception as e:
        print(f"  ❌ DB check failed: {e}")

    print("\n📁 Projects:")
    import brain_agent_v4 as ba
    for pid, root in ba.PROJECTS.items():
        exists = os.path.isdir(str(root))
        print(f"  {pid}={root} {'✅' if exists else '❌'}")

    print("\n🧠 Memory:")
    mem_dir = KB_ROOT / "memory"
    for name in ["MEMORY.md", "PATTERNS.md", "LESSONS.md", "CONTEXT.md"]:
        p = mem_dir / name
        sz = p.stat().st_size if p.exists() else 0
        print(f"  {name}: {sz} bytes")


def cmd_evolve(args):
    from evolve import evolve
    asyncio.run(evolve())


def cmd_ui(args):
    api_py = ROOT / "api.py"
    if api_py.exists():
        print("🚀 Starting API + UI at http://localhost:8000")
        run(f'python "{api_py}"')
    else:
        print("API not found, starting simple chat")
        cmd_chat(args)


def cmd_switch(args):
    print(f"Switching to {args.project}")
    env_path = KB_ROOT / ".env"
    if env_path.exists():
        content = env_path.read_text()
        import re
        if "CURRENT_PROJECT" in content:
            content = re.sub(r"CURRENT_PROJECT=.*", f"CURRENT_PROJECT={args.project}", content, flags=re.M)
        else:
            content += f"\nCURRENT_PROJECT={args.project}\n"
        env_path.write_text(content)
    print(f"✅ Now in {args.project}")


def main():
    parser = argparse.ArgumentParser(prog="sb", description="Second Brain v4 - One CLI does all")
    sub = parser.add_subparsers(dest="cmd")

    p_chat = sub.add_parser("chat", help="Interactive chat like OpenCode")
    p_chat.set_defaults(func=cmd_chat)

    p_agent = sub.add_parser("agent", help="Full multi-agent autonomous task")
    p_agent.add_argument("task", nargs="*", help="Task description")
    p_agent.add_argument("--prompt", type=str, help="Task prompt")
    p_agent.set_defaults(func=cmd_agent)

    p_search = sub.add_parser("search", help="Semantic search")
    p_search.add_argument("query", nargs="+", help="Search query")
    p_search.add_argument("--top-k", type=int, default=6)
    p_search.set_defaults(func=cmd_search)

    p_status = sub.add_parser("status", help="Health check")
    p_status.set_defaults(func=cmd_status)

    p_evolve = sub.add_parser("evolve", help="Self-evolve and improve")
    p_evolve.set_defaults(func=cmd_evolve)

    p_ui = sub.add_parser("ui", help="Start Web UI + API")
    p_ui.set_defaults(func=cmd_ui)

    p_switch = sub.add_parser("switch", help="Switch project")
    p_switch.add_argument("project", help="Project id")
    p_switch.set_defaults(func=cmd_switch)

    if len(sys.argv) == 1:
        cmd_chat(None)
        return

    args = parser.parse_args()
    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()