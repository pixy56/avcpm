# AVCPM Triage & Remediation Plan

**Date:** 2026-04-24  
**Based on:** Multi-model code review by GLM-5.1, MiniMax M2.7, Qwen 3.6:35b, and Claude Code  
**Updated with:** Security triage plan from Claude Code (replacing Gemma 4:31b)  
**Goal:** Move AVCPM from C- → B+ grade in 3 sprints (~8 weeks)

---

## Sprint 1: Security Foundation + Critical Correctness (Weeks 1–3)
**Theme:** "Close every externally-exploitable gap. No bypass should survive."

### Sprint 1 Backlog

| # | Issue | File(s) | Story Pts | Owner | Notes |
|---|-------|---------|-----------|-------|-------|
| 1 | **C1: Enforce auth in `commit()`** | `avcpm_commit.py`, `avcpm_cli.py` | 2 | Security | Wire `validate_session`/`require_auth` into `commit()` entry point; reject unauthenticated callers with typed error. |
| 2 | **C2: Validate `agent_id` everywhere** | `avcpm_security.py` (new), `avcpm_agent.py`, `avcpm_auth.py` | 3 | Security | New `validate_agent_id(s)` (regex `^[a-z0-9_-]{1,64}$`) + `safe_join(base, agent_id)` using `realpath` + `commonpath`. Replace every `os.path.join(..., agent_id, ...)` at ~6 call sites. **Blocks all other security fixes.** |
| 3 | **M-S3: Constant-time session token comparison** | `avcpm_auth.py:237` | 1 | Security | Replace `!=` with `secrets.compare_digest()`. Unit test with mismatched-length inputs. |
| 4 | **M-S2: Bump PBKDF2 → 600k iterations** | `avcpm_security.py` | 2 | Security | Single constant update; embed iteration count in ciphertext header for future bumps. Must land before C4/M-S1. |
| 5 | **C4: Encrypt private keys by default** | `avcpm_agent.py`, `avcpm_security.py`, `avcpm_auth.py`, `avcpm_cli.py` | 3 | Security | `create_agent` encrypts `private.pem` using `cryptography.hazmat` serialization. `--no-encrypt` becomes opt-out with warning. Add `AVCPM_KEY_PASSPHRASE` env var. **Depends on C2 + M-S2.** |
| 6 | **M-S1: Replace AES-CBC with AES-GCM** | `avcpm_security.py` | 3 | Security | New format `v2:salt||nonce||ct||tag`. Read path recognizes `v1` (legacy CBC) for one release. **Co-ships with C4** — same crypto module. |
| 7 | **C3: Verify RSA signatures in ledger integrity** | `avcpm_ledger_integrity.py`, `avcpm_security.py`, `avcpm_agent.py` | 3 | Security | After hash-chain check, call `verify_commit_signature(entry, pubkey)` per entry; fail closed on missing/invalid sig. Expose pubkey lookup helper. |
| 8 | **M-S8: Close TOCTOU in symlink helpers** | `avcpm_security.py` | 3 | Security | Replace `islink()`-then-`open()` with `os.open(path, O_RDONLY | O_NOFOLLOW)` + `os.fstat`. Raise on symlink/mode mismatch. |
| 9 | **C5: Fix commit ID collisions** | `avcpm_commit.py` | 2 | Core VCS | Append microsecond suffix or 4-byte random nonce. Use `O_CREAT | O_EXCL` on ledger write. Prevents data loss + chain breaks. |
| 10 | **M-V1: Add missing `shutil` import** | `avcpm_merge.py` | 1 | Core VCS | `import shutil`. One-liner. |
| 11 | **M-T3: Remove dead code** | `prime_calculator.py`, `test_prime_calculator.py`, `run_tests.py`, `run_review_test.py` | 1 | Testing | Delete files. Update `README.md` test instructions. |

**Sprint 1 Total:** 20 story points  
**Sprint 1 Definition of Done:**
- `commit()` refuses unauthenticated calls
- Fuzzer can't escape agent dir via `agent_id`
- Ledger verifier rejects tampered signature in test
- Private keys encrypted by default; AES-GCM tags catch bit-flips
- Red-team checklist signed off

---

## Sprint 2: Architecture + Core VCS Correctness (Weeks 4–6)
**Theme:** "Make it testable, composable, and correct"

### Sprint 2 Backlog

| # | Issue | File(s) | Story Pts | Owner | Notes |
|---|-------|---------|-----------|-------|-------|
| 12 | **C6: Replace `sys.exit()` with exceptions** | `avcpm_task.py`, `avcpm_merge.py`, `avcpm_cli.py` | 5 | Architecture | Replace all `sys.exit(1)` in library functions with `raise ValueError(...)`. Update CLI handlers to catch and exit. Touch ~15 functions. |
| 13 | **C7: Add `base_dir` to status dashboard** | `avcpm_status.py`, `avcpm_cli.py` | 3 | Architecture | Thread `base_dir` through `get_tasks_by_status()`, `get_ledger_entries()`, `check_system_health()`, all report generators. |
| 14 | **C8: Refactor `status_command()`** | `avcpm_cli.py`, `avcpm_status.py` | 2 | Architecture | Replace `sys.argv` mutation with direct parameter passing. Refactor `status_main()` to accept args dict. |
| 15 | **M-V3: Fix merge (create ledger entry)** | `avcpm_merge.py`, `avcpm_lifecycle.py` | 4 | Core VCS | After copying files to production, create merge commit entry in target branch ledger. Update `parent_commit` pointer. |
| 16 | **M-V2: Fix rollback (verify before delete)** | `avcpm_rollback.py` | 3 | Core VCS | `_get_file_at_commit()` must verify parent staging exists before deleting production file. Add safety check + error. |
| 17 | **M-V4: Fix staging file basename collision** | `avcpm_commit.py` | 2 | Core VCS | Use full relative path (with `/` → `_` encoding) as staging filename, or error on collision. |
| 18 | **M-A1: Remove dual CLI entry point** | `avcpm_task.py` | 2 | Architecture | Delete `if __name__ == "__main__"` block. Route all task commands through unified CLI. |
| 19 | **M-S4: Anti-replay for challenges** | `avcpm_auth.py`, `avcpm_security.py` | 3 | Security | Mark challenge consumed atomically on first verify; store JTI set with TTL; reject replays. **Depends on M-S5 design.** |
| 20 | **M-S5: Atomic writes + file locks** | `avcpm_auth.py`, `avcpm_security.py` | 5 | Security | `fcntl.flock` wrapper; write-temp-then-`os.replace` for JSON; audit every RMW. Shared `atomic_write_json()` helper. |
| 21 | **M-S7: Genesis ledger anchoring** | `avcpm_ledger_integrity.py`, `avcpm_agent.py` | 5 | Security | Hard-code or sign genesis root pubkey; verifier must terminate at anchor. **Depends on C3.** |
| 22 | **M-A2: Blocked tasks can't skip to done** | `avcpm_task.py` | 1 | Architecture | Enforce dependency check for `done` status moves (unless `--force`). |
| 23 | **M-A3: Dependency cycle check on create** | `avcpm_task.py` | 1 | Architecture | Call `would_create_cycle()` when `create_task()` receives `depends_on` parameter. |

**Sprint 2 Total:** 36 story points  
**Sprint 2 Definition of Done:**
- All architecture critical issues closed
- All core VCS correctness fixes merged
- Replay of captured challenge fails
- 50-way concurrent authenticate_agent/session writes produce no lost updates
- Forged genesis entry rejected by verifier

---

## Sprint 3: Testing + Polish (Weeks 7–8)
**Theme:** "Prove it works, harden what's left"

### Sprint 3 Backlog

| # | Issue | File(s) | Story Pts | Owner | Notes |
|---|-------|---------|-----------|-------|-------|
| 24 | **M-T1: Unit tests for `avcpm_commit.py`** | `test_avcpm_commit.py` (new) | 5 | Testing | Cover: commit creation, SHA256 checksums, collision handling, staging file paths, ledger entry format. Mock agent auth. |
| 25 | **M-T2: Unit tests for `avcpm_merge.py`** | `test_avcpm_merge.py` (new) | 5 | Testing | Cover: merge copies files, creates ledger entry, updates branch state, handles missing approval, cross-branch merge. |
| 26 | **M-T5: Standardize on pytest** | All `test_*.py` files | 3 | Testing | Convert `unittest.TestCase` classes to pytest fixtures. Consolidate setup/teardown. Remove `run_integration_tests.py` wrapper. |
| 27 | **M-S6: Guard cleanup against malformed JSON** | `avcpm_auth.py` | 1 | Security | `try/except (json.JSONDecodeError, OSError)`; quarantine bad file to `*.corrupt`; log and continue. |
| 28 | **M-V5: Fix blame correctness** | `avcpm_diff.py` | 3 | Core VCS | Implement per-line commit attribution. Store line ranges in commit metadata, or diff each commit. |
| 29 | **M-A4: Atomic task file moves** | `avcpm_task.py` | 2 | Architecture | Write updated JSON to temp file in target column dir, then atomic rename. |
| 30 | **M-S9: Security audit logging** | New `avcpm_audit.py` | 3 | Security | Append-only log for auth events, commits, merges, rollbacks. Log to `.avcpm/audit.log`. |
| 31 | **M-T6: Adversarial security tests** | `test_avcpm_security.py` (new) | 3 | Testing | Path traversal rejection, malformed JSON handling, session replay, ledger tampering detection. |
| 32 | **Regression + fuzz test pass** | All modules | 2 | Testing | Cover C2/M-S8 paths, AES-GCM round-trip, auth gate fuzzing. |

**Sprint 3 Total:** 24 story points  
**Sprint 3 Definition of Done:**
- All core modules have unit tests
- Corrupt session file does not crash cleanup
- Fuzz + regression suite green
- Security review sign-off

---

## Cross-Sprint Dependency Graph

```
Sprint 1 (Security Foundation)
├── C2 (agent_id validation) ─────┬──► C1 (auth enforcement)
│                                  └──► M-S8 (O_NOFOLLOW hardening)
├── M-S2 (PBKDF2 600k) ───────────┬──► C4 (encrypt by default)
│                                  └──► M-S1 (AES-GCM)
├── C2 + M-S2 ────────────────────► C4 (encrypt by default)
├── M-S3 (compare_digest) ────────► C1
├── C5 (commit ID collisions) ────► M-V3 (merge ledger) ──► M-T2
├── M-V1 (shutil import) ─────────► M-V3
└── C3 (ledger signatures) ───────► M-S7 (genesis anchor) ──► M-T6

Sprint 2 (Architecture + VCS)
├── C6 (exceptions) ────────────────► M-T1/T2 (tests now possible)
├── C7 (base_dir) ─────────────────► C8 (status refactor)
├── M-V3 (merge ledger) ───────────► M-T2
├── M-V2 (rollback safety) ────────► M-T1
├── M-A1 (single CLI) ─────────────► C8
├── M-S4 (anti-replay) ───────────► M-S5 (locks) ──► M-S6 (cleanup)
└── M-S7 (genesis anchor) ─────────► M-T6

Sprint 3 (Testing + Polish)
├── M-T1 (commit tests) ───────────► M-T2 (merge tests)
├── M-S1 (AES-GCM) ───────────────► M-T6
├── M-S8 (O_NOFOLLOW) ────────────► M-T6
└── M-S6 (cleanup guards) ────────► M-T6
```

**Hard dependencies:**
- **C2 → C4, M-S1, M-S8** — Crypto/file work must sit on validated input first
- **M-S2 → C4** — Key-file encryption ships with post-2023 NDF, not rewrap weak keys later
- **C3 → M-S7** — Genesis anchoring meaningless if signatures on later entries never checked
- **M-S4 → M-S5** — Anti-replay schema decides what locks are protecting
- **M-S5 → M-S6** — Cleanup robustness rides on same storage layer

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| C6 (`sys.exit` → exceptions) breaks existing tests | High | Medium | Do C6 first in Sprint 2; fix tests in same PR |
| M-S1 (AES-GCM migration) corrupts existing encrypted keys | Low | High | Write migration script; test on backup copies |
| Sprint 2 scope creep (36 pts aggressive) | Medium | Medium | Cut M-A2, M-A3 to Sprint 3 if behind |
| M-V3 (merge ledger) touches 3+ modules | Medium | High | Pair Core VCS + Architecture leads |
| Missing test fixtures block M-T1/M-T2 | Medium | High | Build fixture library in Sprint 2 alongside C6 |
| Genesis anchoring model undecided (M-S7) | Medium | High | Decide hard-coded pubkey vs. signed manifest in Sprint 2 planning |

---

## Team Assignments

| Role | Model | Sprint Focus |
|------|-------|-------------|
| Security Lead | Claude Code | Sprint 1: C1-C4, M-S1-S3, M-S8. Sprint 2: M-S4-S7. Sprint 3: M-S6, M-S9, M-T6 |
| Core VCS Lead | Qwen 3.6:35b | Sprint 1: C5, M-V1. Sprint 2: M-V2-V4. Sprint 3: M-V5 |
| Architecture Lead | GLM-5.1 | Sprint 2: C6-C8, M-A1-A3. Sprint 3: M-A4 |
| Testing Lead | MiniMax M2.7 | Sprint 1: M-T3. Sprint 2: Test fixtures. Sprint 3: M-T1, M-T2, M-T5, M-T6, regression pass |

---

## Exit Criteria (B+ Grade)

- [ ] All critical issues (C1–C8) closed
- [ ] All security major issues (M-S1–S9) closed
- [ ] All core VCS major issues (M-V1–V5) closed
- [ ] All architecture major issues (M-A1–A4) closed
- [ ] Unit tests for `avcpm_commit.py` and `avcpm_merge.py`
- [ ] pytest standardization complete
- [ ] `bandit -r .` passes with no high-severity warnings
- [ ] CI runs full test suite on every PR
- [ ] Security review re-run: no critical/major findings

---

## Conclusion

**Total: 80 story points across 8 weeks.** Sprint 1 is the heaviest security lift — every fix there closes an externally exploitable gap. Sprint 2 is the most complex due to cross-module architectural changes. Sprint 3 is lighter by design — validation, testing, and polish.

The critical path is: **C2 (agent_id validation) → C1 (auth enforcement) → C3 (ledger signatures) → M-S7 (genesis anchor)**. Without that chain, the trust model collapses.

📄 Full plan saved to `/home/user/.openclaw/workspace/avcpm_triage_plan.md`  
📄 Security-only plan saved to `/tmp/avcpm_security_triage_plan.md`

**Ready to start Sprint 1?**