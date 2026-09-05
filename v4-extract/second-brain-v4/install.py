#!/usr/bin/env python3
"""
Second Brain v4 - Installer & Migrator
Evolves from v3 to v4 with one command
"""
import os
import shutil
from pathlib import Path
import subprocess

def run(cmd):
    print(f"$ {cmd}")
    subprocess.run(cmd, shell=True)

def main():
    print("""
╔══════════════════════════════════════════════════════╗
║  🧠 SECOND BRAIN v4 - Evolution Installer            ║
║  From simple indexer -> Self-evolving multi-agent   ║
╚══════════════════════════════════════════════════════╝
""")
    
    v3_root = Path("X:/second-brain-kb")
    v4_root = Path(__file__).parent
    
    # 1. Copy .env from v3
    if (v3_root / ".env").exists() and not (v4_root / ".env").exists():
        shutil.copy(v3_root / ".env", v4_root / ".env")
        print("✅ Copied .env from v3")
    
    # 2. Create memory dir
    (v4_root / "memory").mkdir(exist_ok=True)
    (v4_root / "logs").mkdir(exist_ok=True)
    (v4_root / "ui").mkdir(exist_ok=True)
    
    # 3. Install deps
    print("\n📦 Installing v4 dependencies...")
    run(f'pip install -r "{v4_root / "requirements.txt"}"')
    
    # 4. Run schema migration
    print("\n🗄️  Migrating Neon schema to v4 (hybrid search + memory)...")
    # Import and run schema
    import sys
    sys.path.insert(0, str(v4_root))
    from chunker_v4 import V4_SCHEMA_SQL
    import asyncio, asyncpg
    from dotenv import load_dotenv
    load_dotenv(v4_root / ".env")
    
    async def migrate():
        conn = await asyncpg.connect(os.getenv("NEON_DSN"))
        try:
            await conn.execute(V4_SCHEMA_SQL)
            print("✅ Schema v4 migrated (chunks_v4, code_graph, conversations, memory, hybrid_search)")
        finally:
            await conn.close()
    
    asyncio.run(migrate())
    
    # 5. Create sb.bat for Windows
    sb_bat = v4_root / "sb.bat"
    sb_bat.write_text(f"""@echo off
cd /d {v4_root}
python sb.py %*
""")
    print(f"✅ Created {sb_bat} - now you can run sb chat from anywhere")
    
    # Add to PATH? Create alias
    print(f"""
✅ v4 Installed!

Next steps:
  1. cd {v4_root}
  2. sb status        # check health
  3. sb chat          # interactive multi-agent
  4. sb agent "add auth from content-engine to lvyy"  # autonomous
  5. sb ui            # start web UI at http://localhost:8000
  6. sb evolve        # self-improve

One terminal commands:
  sb chat    - Like OpenCode, but with memory
  sb agent   - Full autonomous (creates/deletes, runs shell, switches projects)
  sb search "query" - fast search
  sb ui      - Web UI + API

Docker v4 (optional):
  docker compose -f docker-compose.v4.yml up -d --build
  -> API at http://localhost:8000

MCP for OpenCode:
  Add to opencode.json:
  {{
    "mcpServers": {{
      "second-brain": {{
        "command": "python",
        "args": ["{v4_root / 'mcp_server.py'}"]
      }}
    }}
  }}
""")

if __name__ == "__main__":
    main()
