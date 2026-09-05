# Unified LLM Agent - Evolving Instructions

## Current Context

## Projects
- content-engine: X:\content engine\Robin-Content-Engine-v2
- rico: X:\rico\Rico-Your-AI-intelligent-job-hunt-partner-in-the-UAE
- lvyy: C:\Users\loyal\lvyy-ai-sales-agent
- second-brain: X:\unified-llm-local

## System
- API: http://localhost:8000
- Chat: python sb.py chat
- Agent: python sb.py agent "task"
- Search: python sb.py search "query"
- Database: Neon PostgreSQL + pgvector
- Models: deepseek-r1:14b, nomic-embed-text
- Ollama: http://127.0.0.1:11434

## Rules
1. ALWAYS search_brain first before answering about code
2. Switch project when task mentions different repo
3. Create small diffs, test after
4. Update MEMORY.md when you learn user preference
5. If tool fails 2x, try alternative approach
6. Ask before deleting files
7. Commit with conventional commits

## Self-Evolution
- After each task, reflect on what worked/didn't
- Add patterns to PATTERNS.md
- Add failures to LESSONS.md
- Update AGENTS.md for durable state

Last updated: 2026-09-05
