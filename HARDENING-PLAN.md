# Hardened V4 Architecture - Inspection Report & Implementation Plan

## Executive Summary

The existing Second Brain v4 architecture has critical security and reliability issues that must be addressed before production use. The system currently uses global process state (`os.chdir()`), arbitrary shell execution (`shell=True`), lacks path validation, and has no worktree isolation for autonomous agent execution.

## Critical Findings

### 1. GLOBAL PROCESS STATE - CRITICAL
**Location:** `brain_agent_v4.py:348`
**Issue:** `os.chdir(PROJECTS[project_id])` modifies global process state
**Impact:** All file operations become relative to the changed directory, creating race conditions and security vulnerabilities
**Fix:** Remove `os.chdir()` entirely. All operations must use explicit `cwd` parameters or resolve paths against project roots.

### 2. ARBITRARY SHELL EXECUTION - CRITICAL
**Locations:**
- `brain_agent_v4.py:381` - `subprocess.run(command, shell=True, ...)`
- `sb.py:33` - `subprocess.run(cmd, shell=True, **kwargs)`
- `v4-extract/second-brain-v4/install.py:13` - `subprocess.run(cmd, shell=True)`

**Issue:** Arbitrary shell commands executed with `shell=True` allow injection attacks
**Fix:** Replace with typed, allowlisted operations. Use `shell=False` with explicit argument lists.

### 3. NO PATH VALIDATION - HIGH
**Location:** `brain_agent_v4.py:361-370`
**Issue:** `tool_read()` and `tool_write()` accept arbitrary paths without validation
**Impact:** Path traversal (`../`), symlink escapes, absolute paths could access sensitive files
**Fix:** Implement central `resolve()` function that validates all paths against project root.

### 4. NO WORKTREE ISOLATION - HIGH
**Issue:** Agent executes directly in project directories without isolation
**Impact:** Failed changes can corrupt the main repository
**Fix:** Create isolated git worktrees outside repository root for agent execution.

### 5. HYBRID SEARCH NOT WIRED - MEDIUM
**Location:** `brain_agent_v4.py:181-203`
**Issue:** `search_brain()` uses vector-only ordering despite `hybrid_search()` existing in PostgreSQL
**Impact:** Suboptimal search quality
**Fix:** Wire `hybrid_search()` into `search_brain()` with SQL-side filters.

### 6. NO MERGE GOVERNANCE - HIGH
**Issue:** No serialized merge locking mechanism
**Impact:** Concurrent agent runs can cause merge conflicts
**Fix:** Implement repository-level merge lock with baseline SHA verification.

### 7. NO CONTEXT BUILDER - MEDIUM
**Issue:** No token budget, deduplication, or source attribution
**Impact:** Context may exceed model limits, duplicate information
**Fix:** Implement controlled context builder with 32K token budget.

### 8. HARDCODED MODEL ROUTING - LOW
**Location:** `brain_agent_v4.py:118-120`
**Issue:** Models hardcoded (`qwen2.5:7b`)
**Impact:** Cannot easily switch models for different agent roles
**Fix:** Separate model routing from agent logic with configuration.

### 9. DUAL COPY PROBLEM - HIGH
**Issue:** Two divergent copies: `X:\unified-llm-local` (git) vs `X:\second-brain-kb` (live)
**Impact:** Builds against unverified divergent copy
**Fix:** Establish one source-of-truth policy (Git repository).

## Implementation Plan

### Phase 1: Path Security & Shell Hardening

#### 1.1 Create Central Path Resolver
```python
# In a new module: path_security.py
from pathlib import Path
import os


class PathResolver:
    def __init__(self, root: Path):
        self.root = root.resolve()

    def resolve(self, path_str: str) -> Path:
        """Validate and resolve path against root"""
        if os.path.isabs(path_str):
            raise ValueError(f"Absolute path not allowed: {path_str}")

        if ".." in path_str:
            raise ValueError(f"Path traversal not allowed: {path_str}")

        resolved = (self.root / path_str).resolve()

        if not str(resolved).startswith(str(self.root)):
            raise ValueError(f"Path escapes root: {path_str}")

        # Check for symlink escapes
        try:
            if resolved.exists() and resolved.resolve() != resolved:
                raise ValueError(f"Symlink escape not allowed: {path_str}")
        except OSError:
            pass

        return resolved
```

#### 1.2 Replace shell=True Operations
Replace arbitrary shell execution with typed operations:
```python
# Allowed operations
ALLOWED_SHELL_OPS = {
    "read": ["cat", "head", "tail", "wc", "grep"],
    "write": ["tee", "cp"],
    "test": ["pytest", "npm test", "cargo test"],
    "lint": ["ruff", "eslint", "flake8"],
    "typecheck": ["mypy", "tsc", "pyright"],
    "git": ["git status", "git diff", "git log", "git commit"],
}


def tool_shell_typed(operation: str, args: list, cwd: Path):
    """Execute typed, allowlisted operation"""
    if operation not in ALLOWED_SHELL_OPS:
        raise ValueError(f"Operation not allowed: {operation}")

    # Validate command doesn't contain shell metacharacters
    for arg in args:
        if any(c in arg for c in "|;&$`"):
            raise ValueError(f"Shell metacharacters not allowed: {arg}")

    cmd = [ALLOWED_SHELL_OPS[operation][0]] + args
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=120)
```

### Phase 2: Worktree Isolation

#### 2.1 Worktree Manager
```python
# In a new module: worktree.py
import uuid
from pathlib import Path
import subprocess


class WorktreeManager:
    def __init__(self, repo_root: Path):
        self.repo_root = repo_root

    def create_worktree(self, task_id: str) -> Path:
        """Create isolated worktree outside repository"""
        wt_id = f".wt-{task_id[:8]}-{uuid.uuid4().hex[:8]}"
        worktree_path = self.repo_root.parent / wt_id

        # Get baseline SHA
        baseline_sha = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=self.repo_root, capture_output=True, text=True
        ).stdout.strip()

        # Create worktree
        branch = f"agent/{task_id[:32]}"
        subprocess.run(
            ["git", "worktree", "add", "-b", branch, str(worktree_path), baseline_sha],
            cwd=self.repo_root,
            check=True,
        )

        return worktree_path, baseline_sha, branch

    def cleanup_worktree(self, worktree_path: Path, branch: str):
        """Remove worktree and branch"""
        subprocess.run(["git", "worktree", "remove", str(worktree_path)], cwd=self.repo_root)
        subprocess.run(["git", "branch", "-D", branch], cwd=self.repo_root)
```

### Phase 3: Merge Governance

#### 3.1 Merge Lock Manager
```python
# In a new module: merge_lock.py
import fcntl
from pathlib import Path


class MergeLockManager:
    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.lock_file = repo_root / ".merge_lock"

    def acquire_lock(self):
        """Acquire exclusive merge lock"""
        self.lock_file.touch()
        self.lock_fd = open(self.lock_file, "r")
        fcntl.flock(self.lock_fd, fcntl.LOCK_EX)

    def release_lock(self):
        """Release merge lock"""
        fcntl.flock(self.lock_fd, fcntl.LOCK_UN)
        self.lock_fd.close()

    def verify_and_merge(self, baseline_sha: str, commit_sha: str, branch: str):
        """Verify baseline hasn't moved, then merge"""
        current_sha = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=self.repo_root, capture_output=True, text=True
        ).stdout.strip()

        if current_sha != baseline_sha:
            raise RuntimeError(f"Baseline moved: {baseline_sha} -> {current_sha}")

        # Fast-forward merge
        subprocess.run(["git", "merge", "--ff-only", branch], cwd=self.repo_root, check=True)

        # Verify merge result
        merged_sha = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=self.repo_root, capture_output=True, text=True
        ).stdout.strip()

        if merged_sha != commit_sha:
            raise RuntimeError(
                f"Merge verification failed: expected {commit_sha}, got {merged_sha}"
            )
```

### Phase 4: Search & Context

#### 4.1 Wire Hybrid Search
```python
async def search_brain_hybrid(
    query: str, top_k: int = 8, project_id: str = None, language: str = None, chunk_type: str = None
) -> List[Dict]:
    """Hybrid search with RRF and SQL-side filters"""
    query_embedding = await embed(query)
    emb_str = "[" + ",".join(f"{x:.6f}" for x in query_embedding) + "]"

    pool = await _get_pool()
    async with pool.acquire() as conn:
        # Call hybrid_search with filters
        rows = await conn.fetch(
            """SELECT * FROM hybrid_search($1, $2::vector, $3)""", query, emb_str, top_k
        )

        results = [dict(r) for r in rows]

        # Apply SQL-side filters
        if project_id:
            results = [r for r in results if r["project_id"] == project_id]
        if language:
            results = [r for r in results if r.get("language") == language]
        if chunk_type:
            results = [r for r in results if r.get("chunk_type") == chunk_type]

        return results
```

#### 4.2 Context Builder
```python
class ContextBuilder:
    def __init__(self, token_budget: int = 32000):
        self.token_budget = token_budget
        self.seen_hashes = set()

    def build_context(self, search_results: List[Dict], source_attribution: bool = True) -> str:
        """Build context with dedup and token budget"""
        context_parts = []
        current_tokens = 0

        for result in search_results:
            content = result["content"]
            content_hash = hashlib.sha256(content.encode()).hexdigest()

            # Dedup
            if content_hash in self.seen_hashes:
                continue
            self.seen_hashes.add(content_hash)

            # Estimate tokens (rough: 1 token ≈ 4 chars)
            estimated_tokens = len(content) // 4
            if current_tokens + estimated_tokens > self.token_budget:
                break

            # Add with source attribution
            if source_attribution:
                part = f"[{result['project_id']}/{result['file_path']}] {content}"
            else:
                part = content

            context_parts.append(part)
            current_tokens += estimated_tokens

        return "\n\n".join(context_parts)
```

### Phase 5: Agent Pipeline Hardening

#### 5.1 Hardened Agent Executor
```python
class HardenedAgentExecutor:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.path_resolver = PathResolver(project_root)
        self.worktree_manager = WorktreeManager(project_root)
        self.merge_lock = MergeLockManager(project_root)

    async def execute_task(
        self, task: str, auto_commit: bool = False, auto_merge: bool = False
    ) -> Dict:
        """Execute task with full isolation and governance"""
        task_id = uuid.uuid4().hex

        # Create isolated worktree
        worktree_path, baseline_sha, branch = self.worktree_manager.create_worktree(task_id)

        try:
            # Run agent pipeline in worktree
            result = await self._run_agent_pipeline(task, worktree_path)

            # Run deterministic tests
            test_result = await self._run_tests(worktree_path)

            if test_result["success"]:
                # Commit changes
                commit_sha = await self._commit_changes(worktree_path, task)

                if auto_merge:
                    # Acquire merge lock and merge
                    self.merge_lock.acquire_lock()
                    try:
                        self.merge_lock.verify_and_merge(baseline_sha, commit_sha, branch)
                    finally:
                        self.merge_lock.release_lock()

                return {
                    "status": "success",
                    "baseline_sha": baseline_sha,
                    "commit_sha": commit_sha,
                    "worktree": str(worktree_path),
                    "branch": branch,
                }
            else:
                # Preserve failure evidence
                return {
                    "status": "test_failed",
                    "test_output": test_result,
                    "worktree": str(worktree_path),
                    "branch": branch,
                }

        except Exception as e:
            # Never clean up on failure
            return {
                "status": "error",
                "error": str(e),
                "worktree": str(worktree_path),
                "branch": branch,
            }
```

## Security Controls

### 1. Path Security
- [ ] Central `resolve()` function validates all paths
- [ ] Reject absolute paths
- [ ] Reject `../` traversal
- [ ] Reject symlink escapes
- [ ] All operations use explicit project root

### 2. Shell Security
- [ ] Remove `shell=True` from all subprocess calls
- [ ] Implement typed, allowlisted operations
- [ ] Reject shell metacharacters
- [ ] Main repository never writable through agent tools

### 3. Worktree Isolation
- [ ] Agent executes in isolated worktrees
- [ ] Worktrees created outside repository root
- [ ] Baseline SHA captured before changes
- [ ] Cleanup only on success (unless `preserve_on_failure=False`)

### 4. Merge Governance
- [ ] Repository-level serialized merge locking
- [ ] Verify baseline SHA hasn't moved
- [ ] Fast-forward merge only
- [ ] Verify merged SHA matches commit SHA

### 5. Test Authority
- [ ] Pytest exit code is authoritative
- [ ] LLM never declares test success
- [ ] Deterministic test runner with exit codes

### 6. Git Operations
- [ ] Use `git status --porcelain=v1 -z`
- [ ] Support all git status codes
- [ ] Parse filenames with spaces correctly

### 7. Search Hardening
- [ ] Hybrid search wired with RRF
- [ ] SQL-side filters for project_id, language, chunk_type
- [ ] Context builder with token budget
- [ ] Deduplication
- [ ] Source attribution

### 8. Model Routing
- [ ] Separate model routing from agent logic
- [ ] Configuration for architect, editor, fixer, chat, embeddings
- [ ] Preserve Ollama compatibility

## Tests Required

1. **Worktree isolation** - Verify worktree creation and cleanup
2. **Baseline pinning** - Verify SHA captured correctly
3. **Path traversal** - Test rejection of `../` paths
4. **Symlink escape** - Test rejection of symlink escapes
5. **Absolute path** - Test rejection of absolute paths
6. **Filenames with spaces** - Test git status parsing
7. **Git rename parsing** - Test renamed file handling
8. **Git copy parsing** - Test copied file handling
9. **Patch allowlist** - Test unified diff validation
10. **Malformed patch** - Test rejection of invalid diffs
11. **git apply --check** - Test patch validation
12. **Deterministic pytest** - Test exit code authority
13. **Commit SHA** - Test SHA verification
14. **Moved HEAD merge refusal** - Test baseline verification
15. **Serialized merge** - Test merge locking
16. **SHA verification** - Test merge result verification
17. **AUTO_COMMIT=False** - Test branch/worktree preservation
18. **AUTO_MERGE=False** - Test commit without merge
19. **Failure preservation** - Test evidence preservation
20. **Cleanup policy** - Test selective cleanup
21. **Arbitrary shell rejection** - Test shell command filtering
22. **os.chdir absence** - Verify no global state changes
23. **Hybrid RRF search** - Test search quality
24. **SQL-side filtering** - Test filter application
25. **Context budget** - Test token limits
26. **Deduplication** - Test duplicate removal

## Implementation Order

### Phase 1: Foundation (Week 1)
1. Create `path_security.py` with `PathResolver`
2. Create `shell_security.py` with typed operations
3. Remove `os.chdir()` from `brain_agent_v4.py`
4. Update `tool_read()` and `tool_write()` to use path resolver
5. Update `tool_shell()` to use typed operations

### Phase 2: Isolation (Week 2)
1. Create `worktree.py` with `WorktreeManager`
2. Create `merge_lock.py` with `MergeLockManager`
3. Create `HardenedAgentExecutor` class
4. Update agent pipeline to use worktree isolation

### Phase 3: Search & Context (Week 3)
1. Wire `hybrid_search()` into `search_brain()`
2. Implement SQL-side filters
3. Create `ContextBuilder` class
4. Update context generation to use token budget

### Phase 4: Testing (Week 4)
1. Implement all required tests
2. Run security test suite
3. Verify all controls pass
4. Update documentation

## Verification Commands

```bash
# Run ruff linter
ruff check .

# Run pytest
pytest tests/ -v

# Run security tests
pytest tests/test_security.py -v

# Run search evaluation
python eval/run_golden.py --hybrid

# Check git status
git status
git diff
git log -1
```

## Risk Assessment

### Remaining Risks
1. **External dependencies** - Ollama, PostgreSQL availability
2. **Performance** - Worktree creation adds overhead
3. **Complexity** - More moving parts to maintain
4. **Windows compatibility** - Some POSIX-specific code may need adaptation

### Mitigations
1. **Health checks** - Verify external dependencies before execution
2. **Caching** - Reuse worktrees for repeated operations
3. **Simplicity** - Keep each component focused and testable
4. **Cross-platform** - Use `pathlib` and platform-specific code where needed

## Conclusion

The existing Second Brain v4 architecture has critical security issues that must be addressed. The proposed hardening plan provides a comprehensive approach to:

1. **Eliminate global state** - Remove `os.chdir()` and use explicit paths
2. **Prevent shell injection** - Replace arbitrary shell with typed operations
3. **Enforce path security** - Validate all file operations
4. **Isolate agent execution** - Use worktrees for safety
5. **Govern merges** - Serialize and verify merge operations
6. **Improve search quality** - Wire hybrid search with filters
7. **Control context** - Implement token budgets and dedup

With these changes, the system will be production-ready with proper security controls and reliability guarantees.