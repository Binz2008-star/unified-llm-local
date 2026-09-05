"""
🧠 SECOND BRAIN v4 - SOTA Evolution
From simple indexer -> Full Autonomous Self-Evolving Platform

What's new in v4:
1. AST-aware chunking (function/class level, not just 1000 chars)
2. Hybrid search (vector + BM25 keyword + code graph)
3. Multi-agent system (Architect, Editor, Tester, Researcher)
4. Long-term memory that evolves (MEMORY.md, PATTERNS.md, LESSONS.md)
5. Self-evolution - agent can rewrite its own tools
6. FastAPI + Web UI + MCP ecosystem
7. Unified CLI: sb chat / search / agent / evolve / status

Architecture:
  Ollama (embed + chat 16K)
    ↕
  Neon (vectors + BM25 + code graph + conversations)
    ↕
  ┌─────────────────────────────────────┐
  │  sb CLI (one terminal does all)     │
  │  ├─ sb chat    - Q&A like OpenCode │
  │  ├─ sb agent   - Full autonomous   │
  │  ├─ sb search  - Semantic search   │
  │  ├─ sb evolve  - Self-improve     │
  │  └─ sb status  - Health check     │
  └─────────────────────────────────────┘
    ↕
  API (FastAPI) + Web UI + MCP Servers
"""

# v4 file list to create:
# 1. ingest_v4.py - AST chunker + hybrid search + code graph
# 2. memory.py - Long-term memory manager
# 3. brain-agent-v4.py - Multi-agent with self-reflection
# 4. api.py - FastAPI server
# 5. sb.py - Unified CLI (the ONE command)
# 6. mcp_server_v4.py - Enhanced MCP with more tools
# 7. evolve.py - Self-evolution engine
# 8. ui/index.html - Web UI
# 9. docker-compose.v4.yml - Full stack
# 10. AGENT.md - Auto-evolving instructions
