# AVCPM Multi-Model Code Review

**Repository:** https://github.com/pixy56/avcpm
**Date:** 2026-04-24
**Review Team:**
| Reviewer | Model | Focus Area |
|----------|-------|------------|
| Agent 1 | GLM-5.1 | Architecture, CLI, Task Board, Status Dashboard |
| Agent 2 | MiniMax M2.7 | Integration, Lifecycle, Test Infrastructure, Project Health |
| Agent 3 | Qwen 3.6:35b | Core VCS Logic (commits, merge, branch, diff, conflict, rollback, WIP) |
| Agent 4 | Claude Code (Anthropic) | Security, Authentication, Ledger Integrity |

---

## Executive Summary

AVCPM is an ambitious file-based version control and project management system built specifically for AI agent collaboration. The codebase demonstrates clear architectural intent — a Kanban task board linked to commits, SHA256 integrity verification, challenge-response agent authentication, and branch-based feature workspaces. However, across all four review perspectives, a consistent picture emerges: **the project is functionally incomplete and contains multiple critical defects that undermine its core guarantees.**

The most severe cross-cutting issues are:
1. **Authentication is a facade** — challenge-response auth is implemented but never enforced in `commit()`
2. **Path traversal via `agent_id`** — no validation before using attacker-controlled strings as path components
3. **Ledger integrity checks skip RSA signature verification** — the hash chain alone doesn't detect tampering
4. **Private keys are unencrypted by default** — readable by any process with FS access
5. **Commit IDs collide on sub-second commits** — overwriting data and breaking the integrity chain
6. **`sys.exit()` inside library functions** — makes the code untestable and uncomposable
7. **Missing unit tests for core modules** — `avcpm_commit.py` and `avcpm_merge.py` have zero dedicated tests
8. **Dead code and orphaned files** — `prime_calculator.py`, redundant test runners, incomplete stubs

**Overall Grade: C-** — Promising architecture with significant implementation gaps. Not ready for production use with untrusted agents.

---

## Critical Issues (All Reviewers Agree)

### C1. Authentication is imported but never enforced (Security)
- `avcpm_commit.py` imports `require_auth` and `validate_session` but `commit()` never calls them
- Any process can pass `--agent <victim_agent_id>` and have commits signed as that agent
- The challenge-response system is effectively dead code from the caller's perspective
- **Fix:** Add `require_auth(agent_id, base_dir)` at the top of `commit()`

### C2. Path traversal via unvalidated `agent_id` (Security)
- `agent_id` is used directly as a filesystem path component with `os.path.join`
- `agent_id="../../etc/passwd"` → reads/writes arbitrary files
- `encrypt_private_key("../../some/file", ...)` reads the file, encrypts it, then **deletes the original**
- **Fix:** Validate `agent_id` with a strict regex (`^[A-Za-z0-9_-]{1,64}$`) at every public entry point

### C3. Ledger integrity doesn't verify RSA signatures (Security)
- `verify_ledger_integrity()` checks SHA256 chain hashes and `previous_hash` links
- It never calls `verify_commit_signature()`
- An attacker can edit entries, recompute hashes, and the chain validates clean
- **Fix:** Call `verify_commit_signature()` for every entry during integrity checks

### C4. Private keys unencrypted by default (Security)
- `create_agent()` writes `private.pem` in cleartext unless `--encrypt` is passed
- `0o600` only stops other Unix users, not the agent's own compromised processes
- **Fix:** Make encryption mandatory at agent creation; fail closed without a passphrase

### C5. Commit ID collisions (Security + Core VCS)
- `commit_id = datetime.now().strftime("%Y%m%d%H%M%S")` — second resolution
- Two commits in the same second share the same filename; second silently overwrites the first
- Breaks the ledger chain because overwritten entry's `entry_hash` no longer matches `previous_hash` of the next commit
- **Fix:** Append microsecond suffix or random nonce; use `O_CREAT | O_EXCL` to detect collisions

### C6. `sys.exit()` inside library functions (Architecture)
- `avcpm_task.py`: `create_task()`, `move_task()`, `deps_add()`, `deps_remove()` all call `sys.exit(1)` on error
- `avcpm_merge.merge()` also calls `sys.exit()`
- Makes unit testing require `pytest.raises(SystemExit)`; makes programmatic error handling impossible
- **Fix:** Replace `sys.exit(1)` with `raise ValueError(...)`; let the CLI layer catch and exit

### C7. Status dashboard ignores `base_dir` (Architecture)
- `avcpm_status.py` hardcodes `DEFAULT_BASE_DIR = ".avcpm"` in every function
- `avcpm status --base-dir /custom` silently does nothing
- Tests must monkey-patch module-level variables
- **Fix:** Pass `base_dir` through all status functions

### C8. CLI `status_command()` rewrites `sys.argv` (Architecture)
```python
def status_command(args):
    sys.argv = ['avcpm_status']
    ...
    status_main()
```
- Mutates global `sys.argv`; breaks if other code reads it; discards already-parsed `--base-dir`
- **Fix:** Refactor `status_main()` to accept parameters directly

---

## Major Issues

### Core VCS
- **Missing `shutil` import in `avcpm_merge.py`** — will `NameError` on any merge call
- **Rollback reads file after deleting it** — `_get_file_at_commit()` reads parent commit's staging, but if staging was removed, rollback silently fails and deletes the production file instead
- **Merge bypasses commit metadata** — copies files to production but creates no ledger entry for the merge; target branch's ledger is unmodified
- **Commit overwrites staging files by basename** — `dir1/foo.txt` and `dir2/foo.txt` in the same commit collide silently
- **Blame is trivially wrong** — attributes all lines to the most recent commit, not per-line tracking
- **All ledger files loaded into memory on validation** — O(n) glob+parse every call, no caching

### Security
- **AES-256-CBC has no MAC** — malleable ciphertext; vulnerable to bit-flipping
- **PBKDF2 only 100k iterations** — below 2023 NIST floor of 600k; offline brute-force feasible
- **Non-constant-time session token comparison** — `!=` instead of `secrets.compare_digest`
- **Challenge replay** — no anti-replay state; concurrent `authenticate_agent` calls both succeed
- **Race conditions in session/challenge storage** — read-modify-write with no locks; non-atomic JSON writes
- **Malformed JSON crashes cleanup** — one bad file in `agent_sessions/` aborts the entire sweep
- **Genesis ledger not anchored** — attacker can prepend a forged genesis entry
- **TOCTOU in symlink helpers** — `islink()` check then `open()` is raceable

### Architecture
- **Dual CLI entry points** — `avcpm_task.py` has its own `__main__` with manual `sys.argv` parsing; inconsistent with unified `avcpm_cli.py`
- **Blocked tasks can move directly to `done`** — dependency check only enforced for `in-progress` and `review`
- **Dependency cycle check bypassed on create** — `create_task()` with comma-separated `depends_on` never calls `would_create_cycle()`
- **No atomicity for task file moves** — `shutil.move()` then re-open to write JSON; crash mid-write leaves stale data
- **`format_task_row` inconsistent truncation** — uses `title` key but `create_task()` stores `description`

### Testing / Project Health
- **Missing unit tests for core modules** — `avcpm_commit.py` and `avcpm_merge.py` have zero dedicated tests
- **Dead code** — `prime_calculator.py` and `test_prime_calculator.py` are completely unrelated; the test has a broken import
- **Redundant test runners** — `run_tests.py`, `run_integration_tests.py`, `run_review_test.py` overlap confusingly
- **Framework inconsistency** — mix of `unittest.TestCase` and `pytest` fixtures across test files
- **Incomplete integration test stubs** — Phase 2 tests are `pass` placeholders
- **No end-to-end merge test** — no test verifies merge actually copies files or creates ledger entries

---

## Strengths (Confirmed Across All Reviewers)

1. **Kanban task board design** — directory-per-column with JSON files is simple, human-readable, and git-friendly
2. **Dependency system** — cycle detection via DFS, `is_blocked`/`can_progress` queries, ASCII tree visualization
3. **Unified CLI ambition** — comprehensive `argparse` structure covering all subcommands
4. **Status dashboard health checks** — orphaned ledger entries, duplicate task IDs, untracked staging files
5. **Branch system** — parent chain tracking, circular-reference detection, rename cascading
6. **WIP tracking** — claim/release with stale expiration, glob-based batch claiming, path normalization
7. **Conflict detection** — three-way merge with `SequenceMatcher`, multiple conflict types, four resolution strategies
8. **Rollback with backups** — soft/hard reset, per-file restore, auto-backup before destructive ops
9. **Diff/History system** — full git-like diff, side-by-side formatting, blame, file history, branch comparison
10. **Cryptographic primitives** — RSA-PSS + SHA256 signatures, `secrets.token_hex` for nonces, symlink-aware file helpers
11. **Comprehensive documentation** — README, AGENTS.md, SOUL.md, design docs, phase roadmaps

---

## Testing Gaps (Cross-Reviewer Consensus)

| Gap | Severity | Notes |
|-----|----------|-------|
| No merge end-to-end test | 🔴 Critical | `test_avcpm_merge.py` doesn't exist |
| No encryption round-trip tests | 🔴 Critical | `_encrypt_data`/`_decrypt_data` have zero tests |
| No auth path tests | 🔴 Critical | `avcpm_auth.py` entirely untested |
| No ledger integrity adversarial tests | 🔴 Critical | No mutation + re-verification test |
| No path traversal rejection tests | 🔴 Critical | Would have caught C2 |
| No commit collision test | 🔴 Critical | Two commits same second |
| No concurrency tests | 🟡 Major | Sessions, challenges, ledger races |
| No symlink/TOCTOU tests | 🟡 Major | `avcpm_security.py` untested directly |
| No cross-branch merge test | 🟡 Major | Feature → main with file copies |
| No cleanup negative tests | 🟡 Major | Malformed JSON in `agent_sessions/` |
| No `sanitize_path` adversarial inputs | 🟢 Minor | URL-encoded, NUL bytes, long paths |

---

## Recommendations (Prioritized)

### Must Fix Before Any Production Use
1. **Enforce authentication in `commit()`** — call `require_auth()` or derive from validated session (C1)
2. **Validate `agent_id` everywhere** — strict regex before any filesystem operation (C2)
3. **Verify RSA signatures during ledger integrity checks** (C3)
4. **Make private-key encryption mandatory** (C4)
5. **Replace `sys.exit()` with exceptions** in all library functions (C6)
6. **Add `base_dir` parameter** to status dashboard functions (C7)
7. **Fix commit ID collisions** — microsecond suffix + `O_CREAT | O_EXCL` (C5)
8. **Add missing `shutil` import** in `avcpm_merge.py`
9. **Remove dead code** — delete `prime_calculator.py`, `test_prime_calculator.py`, redundant runners
10. **Write unit tests for `avcpm_commit.py` and `avcpm_merge.py`** — the two most critical untested modules

### Should Fix Before Broader Rollout
11. **Switch AES-CBC to AES-GCM** for private-key encryption (M1)
12. **Bump PBKDF2 to ≥600k iterations** or migrate to Argon2id (M2)
13. **`secrets.compare_digest` for session tokens** (M3)
14. **Atomic file writes + file locks** for sessions, challenges, and ledger entries (M4, M5)
15. **Genesis anchoring** for ledger chain (M8)
16. **`O_NOFOLLOW` on read/write paths** to close TOCTOU window (M9)
17. **Refactor `status_command()`** to not mutate `sys.argv`
18. **Fix rollback logic** — verify parent staging exists before deleting production file
19. **Fix merge** — create ledger entry for merge, update target branch state
20. **Standardize on pytest** — consolidate test framework

### Hygiene / Future Work
21. Add `logging` for security events; append-only audit log
22. Add the "compromised agent commits as victim" end-to-end test
23. Run `bandit -r .` static analysis and add to CI
24. Document the threat model explicitly in `AVCPM.md`
25. Resolve the dual CLI entry point split (`avcpm_task.py` `__main__` vs `avcpm_cli.py`)

---

## Conclusion

AVCPM has solid architectural bones and a clear vision, but the implementation has too many critical gaps to be trusted with anything important right now. The good news: most issues are fixable with focused effort. The authentication and path-safety fixes are small code changes with outsized impact. The testing gaps are the biggest long-term risk — commit and merge are the two most critical modules and have zero dedicated tests.

**Estimated remediation effort:** 2-3 focused sprints to reach a B+ grade.
