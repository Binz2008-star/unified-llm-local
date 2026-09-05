.PHONY: setup test lint format reindex eval docker clean

setup:
	python -m venv .venv || true
	.venv/Scripts/pip install -r requirements.txt
	.venv/Scripts/pip install ruff pytest
	ollama list | grep -q "qwen2.5:7b" || ollama pull qwen2.5:7b
	ollama list | grep -q "nomic-embed-text" || ollama pull nomic-embed-text
	cp -n .env.example .env || true
	@echo "setup done — fill .env (NEON_DSN) and run make test"

test:
	ruff check . --output-format=github || true
	ruff format --check . || true
	pytest -q
	python eval/run_golden.py --top-k 8 | tail -5

lint:
	ruff check . --fix
	ruff format .

reindex:
	python reindex_v4.py --scan
	python reindex_v4.py

eval:
	python eval/run_golden.py
	python eval/run_golden.py --hybrid

docker:
	docker compose -f docker-compose.v4.yml build
	docker compose -f docker-compose.v4.yml up -d && sleep 5 && curl -f http://localhost:8000/api/status | jq . || curl -f http://localhost:8000/api/status

clean:
	rm -rf .venv .pytest_cache .ruff_cache pgdata ollama_data
