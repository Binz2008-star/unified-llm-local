# Second Brain v4 - Inspection Summary

## Status: NOT READY — CRITICAL BLOCKERS

## Critical Blockers Found

### 1. GLOBAL PROCESS STATE - `os.chdir()`
**File:** `brain_agent_v4.py:348`
**Code:** `os.chdir(PROJECTS[project_id])`
**Impact:** Modifies global process state, creates race conditions
**Action:** Remove immediately - must not exist in autonomous execution path

### 2. ARBITRARY SHELL EXECUTION - `shell=True`
**Locations:**
- `brain_agent_v4.py:381` - `subprocess.run(command, shell=True, ...)`
- `sb.py:33` - `subprocess.run(cmd, shell=True, **kwargs)`
- `v4-extract\second-brain-v4\install.py:13` - `subprocess.run(cmd, shell=True)`

**Impact:** Shell injection attacks possible
**Action:** Replace with typed, allowlisted operations

### 3. NO PATH VALIDATION
**File:** `brain_agent_v4.py:361-370`
**Functions:** `tool_read()`, `tool_write()`
**Impact:** Path traversal, symlink escapes, absolute path access
**Action:** Implement central `resolve()` function

### 4. NO WORKTREE ISOLATION
**Issue:** Agent executes directly in project directories
**Impact:** Failed changes corrupt main repository
**Action:** Create isolated git worktrees outside repo root

### 5. HYBRID SEARCH NOT WIRED
**File:** `brain_agent_v4.py:181-203`
**Issue:** Uses vector-only ordering despite `hybrid_search()` existing
**Impact:** Suboptimal search quality
**Action:** Wire `hybrid_search()` with SQL-side filters

### 6. NO MERGE GOVERNANCE
**Issue:** No serialized merge locking
**Impact:** Concurrent agent runs cause conflicts
**Action:** Implement merge lock with baseline SHA verification

### 7. NO CONTEXT BUILDER
**Issue:** No token budget, deduplication, or source attribution
**Impact:** Context may exceed model limits
**Action:** Implement controlled context builder with 32K budget

## Security Assessment

### Existing Controls (PASS)
- Shell denylist (basic pattern blocking)
- Test failure gate (consecutive failure detection)
- Fingerprint dedup (content deduplication)
- Failure preservation (worktrees preserved on failure)

### Missing Controls (FAIL)
- Path validation (`resolve()` function)
- Shell allowlist (only denylist exists)
- Worktree isolation (not implemented)
- Merge governance (no locking)
- Token budget (no context limiting)
- Source attribution (not implemented)

## Test Results

### Existing Tests
- `test_failure_gate.py` - PASSED
- `test_memory_dedup.py` - PASSED

### Ruff Linter
- **144 errors found** (110 fixable with `--fix`)
- Import ordering issues
- Unused imports
- Deprecated typing imports
- Type annotation issues

## Git Status

### Current State
- **Branch:** master
- **Commit:** `74de281437559a5ffa48748be3159569409139d4`
- **Message:** "chore: ci stability check — second green run"
- **Status:** Clean (only untracked inspection files)

### Files Created
- `HARDENING-PLAN.md` - Detailed implementation plan
- `INSPECTION-REPORT.md` - Security assessment
- `SUMMARY.md` - This file

## Implementation Plan

### Phase 1: Path Security & Shell Hardening (Week 1)
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

## Risk Assessment

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

## Timeline
- **Phase 1 (Week 1):** Path security & shell hardening
- **Phase 2 (Week 2):** Worktree isolation & merge governance
- **Phase 3 (Week 3):** Search & context hardening
- **Phase 4 (Week 4):** Testing & verification

## Next Steps

1. **Immediate:** Remove `os.chdir()` from `brain_agent_v4.py`
2. **Immediate:** Replace `shell=True` with typed operations
3. **Short-term:** Implement path validation
4. **Medium-term:** Implement worktree isolation
5. **Long-term:** Complete all hardening phases

## Conclusion

The Second Brain v4 architecture has critical security vulnerabilities that must be addressed before production deployment. The inspection has identified specific blockers and a clear path to remediation. With the proposed hardening plan, the system can achieve production readiness within 4 weeks.