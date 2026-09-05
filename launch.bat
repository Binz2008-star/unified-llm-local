@echo off
cd /d X:\unified-llm-local
echo Starting Unified LLM Local via Docker...
docker compose -f docker-compose.v4.yml up -d
echo.
echo Everything is running!
echo Dashboard: http://localhost:3000
echo API: http://localhost:8000
echo Chat: python sb.py chat
echo.
echo To stop: docker compose -f docker-compose.v4.yml down
pause
