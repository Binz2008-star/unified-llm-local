# Final Inspection Report - Second Brain v4

## Executive Summary

The Second Brain v4 codebase has been inspected for security vulnerabilities, reliability issues, and architectural gaps. **Critical issues found that must be addressed before production use.**

## Critical Findings

### 1. GLOBAL PROCESS STATE - CRITICAL SEVERITY
**File:** `brain_agent_v4.py:348`
**Code:** `os.chdir(PROJECTS[project_id])`
**Impact:** Modifies global process state, creating race conditions and security vulnerabilities
**Status:** **FIX REQUIRED** - Must remove `os.chdir()` entirely

### 2. ARBITRARY SHELL EXECUTION - CRITICAL SEVERITY
**Locations:**
- `brain_agent_v4.py:381` - `subprocess.run(command, shell=True, ...)`
- `sb.py:33` - `subprocess.run(cmd, shell=True, **kwargs)`
- `v4-extract/second-brain-v4/install.py:13` - `subprocess.run(cmd, shell=True)`

**Impact:** Shell injection attacks possible through malicious commands
**Status:** **FIX REQUIRED** - Must replace with typed, allowlisted operations

### 3. NO PATH VALIDATION - HIGH SEVERITY
**File:** `brain_agent_v4.py:361-370`
**Functions:** `tool_read()`, `tool_write()`
**Impact:** Path traversal (`../`), symlink escapes, absolute paths could access sensitive files
**Status:** **FIX REQUIRED** - Must implement central path resolver

### 4. NO WORKTREE ISOLATION - HIGH SEVERITY
**Issue:** Agent executes directly in project directories without isolation
**Impact:** Failed changes can corrupt the main repository
**Status:** **FIX REQUIRED** - Must create isolated git worktrees

### 5. HYBRID SEARCH NOT WIRED - MEDIUM SEVERITY
**File:** `brain_agent_v4.py:181-203`
**Function:** `search_brain()`
**Issue:** Uses vector-only ordering despite `hybrid_search()` existing in PostgreSQL
**Impact:** Suboptimal search quality
**Status:** **FIX REQUIRED** - Must wire `hybrid_search()` with SQL-side filters

### 6. NO MERGE GOVERNANCE - HIGH SEVERITY
**Issue:** No serialized merge locking mechanism
**Impact:** Concurrent agent runs can cause merge conflicts
**Status:** **FIX REQUIRED** - Must implement merge lock with baseline SHA verification

### 7. NO CONTEXT BUILDER - MEDIUM SEVERITY
**Issue:** No token budget, deduplication, or source attribution
**Impact:** Context may exceed model limits, duplicate information
**Status:** **FIX REQUIRED** - Must implement controlled context builder

## Security Controls Assessment

### PASS - Existing Controls
1. **Shell denylist** - Basic pattern blocking exists
2. **Test failure gate** - Consecutive failure detection
3. **Fingerprint dedup** - Content deduplication for memory
4. **Failure preservation** - Worktrees preserved on failure

### FAIL - Missing Controls
1. **Path validation** - No `resolve()` function
2. **Shell allowlist** - Only denylist exists
3. **Worktree isolation** - Not implemented
4. **Merge governance** - No locking mechanism
5. **Token budget** - No context limiting
6. **Source attribution** - Not implemented

## Files Modified

### Critical Files
- `brain_agent_v4.py` - Remove `os.chdir()`, add path validation, shell hardening
- `sb.py` - Remove `shell=True`
- `v4-extract/second-brain-v4/install.py` - Remove `shell=True`

### New Files Required
- `path_security.py` - Central path resolver
- `shell_security.py` - Typed shell operations
- `worktree.py` - Worktree manager
- `merge_lock.py` - Merge governance
- `context_builder.py` - Token-budgeted context
- `hardened_agent.py` - Hardened agent executor

## Test Coverage

### Existing Tests
- `test_failure_gate.py` - Failure detection
- `test_memory_dedup.py` - Fingerprint dedup

### Required Tests
1. Worktree isolation
2. Baseline pinning
3. Path traversal
4. Symlink escape
5. Absolute path rejection
6. Filenames with spaces
7. Git rename parsing
8. Git copy parsing
9. Patch allowlist
10. Malformed patch rejection
11. git apply --check
12. Deterministic pytest authority
13. Commit SHA verification
14. Moved HEAD merge refusal
15. Serialized merge
16. SHA verification
17. AUTO_COMMIT=False
18. AUTO_MERGE=False
19. Failure preservation
20. Cleanup policy
21. Arbitrary shell rejection
22. os.chdir absence
23. Hybrid RRF search
24. SQL-side filtering
25. Context budget
26. Deduplication

## Git Status

### Baseline SHA
```
commit: [To be captured before changes]
branch: main
```

### Repository State
- **Clean:** Yes
- **Modified files:** None (inspection only)
- **Untracked files:** `HARDENING-PLAN.md`, `INSPECTION-REPORT.md`

## Search Status

### Hybrid Search
- **Exists in PostgreSQL:** Yes (`hybrid_search()` function)
- **Wired in search_brain():** No (vector-only)
- **SQL-side filters:** Not implemented
- **RRF implementation:** Yes (in PostgreSQL function)

## Remaining Risks

### High Risk
1. **Global state modification** - `os.chdir()` affects all threads
2. **Shell injection** - Arbitrary commands can be executed
3. **Path traversal** - No validation on file operations

### Medium Risk
4. **Repository corruption** - No isolation for agent changes
5. **Merge conflicts** - No governance for concurrent operations
6. **Context overflow** - No token budgeting

### Low Risk
7. **Search quality** - Hybrid search not utilized
8. **Model routing** - Hardcoded models
9. **Dual copy** - Potential divergence

## VERDICT

**NOT READY — BLOCKERS LISTED**

### Blockers
1. `os.chdir()` must be removed
2. `shell=True` must be replaced with typed operations
3. Path validation must be implemented
4. Worktree isolation must be implemented
5. Merge governance must be implemented

### Required Actions
1. Implement `path_security.py` with `PathResolver`
2. Implement `shell_security.py` with typed operations
3. Remove `os.chdir()` from `brain_agent_v4.py`
4. Implement `worktree.py` with `WorktreeManager`
5. Implement `merge_lock.py` with `MergeLockManager`
6. Wire `hybrid_search()` into `search_brain()`
7. Implement `ContextBuilder` with token budget
8. Add comprehensive test suite

### Timeline
- **Phase 1 (Week 1):** Path security & shell hardening
- **Phase 2 (Week 2):** Worktree isolation & merge governance
- **Phase 3 (Week 3):** Search & context hardening
- **Phase 4 (Week 4):** Testing & verification

## Verification Commands

```bash
# Run linter
ruff check .

# Run tests
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

## Conclusion

The Second Brain v4 architecture has critical security vulnerabilities that must be addressed before production deployment. The inspection has identified specific blockers and a clear path to remediation. With the proposed hardening plan, the system can achieve production readiness within 4 weeks.