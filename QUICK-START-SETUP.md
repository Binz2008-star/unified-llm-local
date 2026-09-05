# 🧠 Second Brain KB - Complete Setup Guide

**Goal**: End-to-end semantic KB + autonomous agent system for code reuse across 3 projects

---

## Phase 1: Prerequisites Check (5 min)

### 1.1 Python Environment
```powershell
python --version  # Must be 3.9+
python -m pip --version  # Verify pip works
```

### 1.2 Ollama (Embedding + Chat)
```powershell
ollama --version
ollama list
```

**Required models**:
- `nomic-embed-text` (768-dim embeddings)
- `qwen2.5-coder:32b` (chat/reasoning)

**If missing, pull them**:
```powershell
ollama pull nomic-embed-text
ollama pull qwen2.5-coder:32b
```

**Verify Ollama is running**:
```powershell
curl http://127.0.0.1:11434/api/tags
```

### 1.3 PostgreSQL (Neon)
- DB already set up: `postgresql://neondb_owner:...@ep-empty-paper-avokj61h-pooler.c-11.us-east-1.aws.neon.tech`
- Verify: Try connecting with `psql` or run schema once

### 1.4 Local Projects
All 3 exist ✅:
```powershell
ls X:\content engine\Robin-Content-Engine-v2
ls C:\Users\loyal\lvyy-ai-sales-agent
ls X:\rico
```

---

## Phase 2: Install Dependencies (3 min)

```powershell
cd X:\second-brain-kb

# Install CPU-only PyTorch + all deps
pip install -r requirements.txt

# If that fails, install individually:
pip install --extra-index-url https://download.pytorch.org/whl/cpu torch asyncpg aiohttp watchdog tiktoken python-dotenv rich sentence-transformers huggingface_hub
```

**Expected output**: All packages installed without errors ✅

---

## Phase 3: Database Setup (2 min - ONE TIME ONLY)

### 3.1 Create Schema
```powershell
# Option A: Using psql (if installed)
psql $env:NEON_DSN -f schema.sql

# Option B: Using Python (easier on Windows)
python -c "
import asyncpg
import asyncio
from pathlib import Path

async def setup():
    conn = await asyncpg.connect(Path('.env').read_text().split('NEON_DSN=')[1].split('\n')[0])
    schema = Path('schema.sql').read_text()
    await conn.execute(schema)
    print('✅ Schema created!')
    await conn.close()

asyncio.run(setup())
"
```

### 3.2 Verify Table Exists
```powershell
python -c "
import asyncpg, asyncio, os
from dotenv import load_dotenv

load_dotenv()

async def check():
    conn = await asyncpg.connect(os.getenv('NEON_DSN'))
    tables = await conn.fetch('SELECT tablename FROM pg_tables WHERE schemaname=\'public\'')
    print('Tables:', [t['tablename'] for t in tables])
    await conn.close()

asyncio.run(check())
"
```

---

## Phase 4: Ingest Code (5-15 min)

### Option A: Quick Ingest (Ollama, CPU only)
```powershell
python ingest.py
# Output: Indexing X:\content engine...
#         Indexed content-engine: 456 chunks
#         Indexing C:\Users\loyal\lvyy-ai-sales-agent...
#         Indexed lvyy: 234 chunks
#         Indexing X:\rico...
#         Indexed rico: 189 chunks
# ✅ Total: 879 chunks
```

### Option B: Better Quality (HuggingFace embeddings)
```powershell
python ingest_hf.py
# First run: ~30 seconds (downloads 400MB model, cached after)
# Output: Same as above but with better embeddings
```

### Option C: Tree-Sitter (Experimental, symbol-level)
```powershell
python Ingest-Heimdall.py
# Output: Chunks by symbol, with STRONG/WEAK/REBUILT/STALE verdicts
```

**Expected result**: ~879 chunks indexed ✅

---

## Phase 5: Test Semantic Search (2 min)

```powershell
python query.py
# You will see:
# 🔍 Query: 

# Type a test query:
# > find auth middleware
# [content-engine/src/api.py] JWT verification middleware...
# [lvyy/src/auth.py] Token handling logic...
# [rico/middleware.py] Auth decorator...

# Type: exit
```

---

## Phase 6: Run Terminal Agent (Interactive)

```powershell
python brain-agent.py
# You will see:
# 📁 Projects: ['content-engine', 'lvyy', 'rico', 'second-brain']
# 📍 Current: lvyy
# 🤗 HF: Salesforce/SFR-Embedding-Code-400M_R | Chat: qwen2.5-coder:32b
#
# [lvyy]$ 

# Try a task:
# > add JWT auth from content-engine
# (Agent will search, read source, write adapted code to lvyy)

# Or one-shot:
```

```powershell
python brain-agent.py "add JWT auth from content-engine to lvyy"
```

---

## Phase 7: IDE Integration (MCP Servers)

### Copy MCP config to Claude
```powershell
copy Opencode-Final.json "$env:APPDATA\Claude\claude_desktop_config.json"
```

**Inside Claude/Cursor/OpenCode**: You now have access to:
- `@second-brain` — semantic search
- `@filesystem` — read/write files in projects
- `@git` — commit, status
- And 8 other standard MCPs

---

## ✅ Full Test Checklist

- [ ] Python 3.9+ installed
- [ ] Ollama running with required models
- [ ] Neon PostgreSQL accessible
- [ ] `pip install -r requirements.txt` succeeded
- [ ] Schema created in Neon
- [ ] `python ingest.py` completed (879+ chunks)
- [ ] `python query.py` finds results
- [ ] `python brain-agent.py "test task"` runs
- [ ] MCP config copied to IDE

---

## 🔧 Troubleshooting

| Issue | Fix |
|-------|-----|
| `ModuleNotFoundError: asyncpg` | `pip install asyncpg` |
| `Connection refused: 11434` | Start Ollama: `ollama serve` |
| `SSL error connecting to Neon` | Make sure sslmode=require in .env |
| `Model not found: nomic-embed-text` | `ollama pull nomic-embed-text` |
| `CUDA OOM` | Already CPU-only ✅, just run it |
| `HF model 400MB download fails` | Use `ingest.py` (Ollama) instead |
| `Tree-sitter build fails` | `pip install tree-sitter tree-sitter-python` |

---

## 🚀 Next Steps

1. **Search patterns**: `python query.py` and explore what's indexed
2. **Create new project**: `python Sb-New.py` → scaffold nextjs/fastapi/python
3. **Autonomous tasks**: `python brain-agent.py "your task"` 
4. **IDE integration**: Copy MCP config, use `@second-brain` in Claude
5. **Docker deployment**: `docker-compose -f Docker-Compose-Hf.yml up` (containerized)

---

## 📊 Architecture Summary

```
3 Local Projects → Ingestion (Ollama/HF/Tree-sitter) → Neon PgVector
                                                       ↓
                                      Query.py (CLI search)
                                      Brain-Agent.py (autonomous agent)
                                      MCP Servers (IDE integration)
```

**Time to full setup**: ~20-30 minutes (mostly downloads and ingestion)
**Result**: Fully functional semantic KB + agent ready for code reuse automation

