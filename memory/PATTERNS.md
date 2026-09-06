# PATTERNS — Cross-Repo Code Patterns

## Agent Pipeline Pattern
```python
# Every agent task follows this flow:
1. search_brain(query) → context
2. Architect plans (uses context)
3. Editor writes code (uses plan + tools)
4. Tester runs tests (uses pytest)
5. Memory saves lessons (uses LESSONS.md)
```

## Tool Function Pattern
```python
# All tool functions follow this signature:
def tool_<name>(<args>, workspace: Path = None) -> str:
    """Returns human-readable result string."""
    # Validate inputs
    # Execute operation
    # Return result or error message
```

## Error Handling Pattern
```python
# Failure gate: N consecutive failures → abort
max_failures = _settings.max_consecutive_tool_failures  # default 3
consecutive_failures = 0
# On failure: consecutive_failures += 1, sleep, retry
# On success: consecutive_failures = 0
# If consecutive_failures >= max: return "[AGENT GAVE UP]"
```

## Security Pattern
```python
# Every file operation:
1. validate_path(file_path, workspace)  # bounds check
2. assert_mutation_allowed(path, operation)  # protected file check
3. Execute operation
4. Audit log entry
```

## Database Pattern
```python
# Dual-pool: local for vectors, Neon for metadata
pool = await _get_local_pool()  # pgvector Docker
async with pool.acquire() as conn:
    rows = await conn.fetch("SELECT ... FROM hybrid_search(...)")
```

## Docker Pattern
```python
# Container env vars override .env file
# docker-compose.v4.yml defines base
# docker-compose.override.yml overrides for dev (host Ollama)
# Runtime: docker exec second-brain-v4 env | grep MODEL
```

## Test Pattern
```python
# Unit tests: tmp_path fixture, no external deps
# Integration tests: real git repos, subprocess, DB connections
# Performance tests: throughput gates (ops/sec)
# Security tests: injection attempts, path traversal, etc.
```
