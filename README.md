# Unified LLM Local

Local LLM with unified knowledge from all projects.

## Projects
- **Second Brain v4** — Knowledge base, multi-agent, hybrid search
- **Rico AI** — UAE job hunt automation
- **Robin Content Engine** — Gaming Shorts production pipeline

## Models (Ollama)
- `deepseek-r1:14b` — Chat/reasoning
- `nomic-embed-text` — Embeddings
- `qwen2.5:7b` — Lightweight chat

## Quick Start

```bash
# Start the API server (background)
python api.py

# Or use launch scripts
.\launch.bat      # Windows
./launch.ps1      # PowerShell

# Interactive chat
python sb.py chat

# Multi-agent task
python sb.py agent "add authentication to rico"

# Search all project knowledge
python sb.py search "OAuth token flow"

# Self-evolution
python sb.py evolve
```

## Endpoints
- API: `http://localhost:8000`
- Health: `http://localhost:8000/api/status`
- Search: `POST http://localhost:8000/api/search`
- Chat: `POST http://localhost:8000/api/chat`
- Agent: `POST http://localhost:8000/api/agent`

## Database
- Neon PostgreSQL with pgvector
- 9,592+ code chunks indexed
- 3 projects: content-engine, rico, second-brain

## GitHub
- Repo: https://github.com/Binz2008-star/unified-llm-local
