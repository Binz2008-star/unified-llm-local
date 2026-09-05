@echo off
cd /d X:\unified-llm-local
echo Starting Unified LLM Local...
start "Second Brain API" python api.py
echo API running on http://localhost:8000
echo Chat: python sb.py chat
