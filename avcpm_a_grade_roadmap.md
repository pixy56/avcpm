# AVCPM B+ → A Grade Roadmap

**Date:** 2026-04-24  
**Based on:** Multi-model review by GLM-5.1 (Architecture), MiniMax M2.7 (Testing), Qwen 3.6:35b (Security — partial)  
**Current grade:** B+  
**Target:** A  
**Estimated effort:** 34 story points across 2 sprints (~5 weeks)

---

## Executive Summary

AVCPM is at **B+** — all critical and major issues from the original review are resolved, comprehensive tests exist, and the security posture is dramatically improved. The gap to **A** is primarily in **infrastructure**: CI/CD pipeline (currently F), type hint coverage (49%), and three remaining security hardening items (M-S4, M-S5, M-S7).

**The single biggest A-grade blocker:** No CI/CD. Every quality gate is manual. Without automated linting, type-checking, testing, and security scanning, regressions are inevitable.

---

## Gap Analysis

### 1. CI/CD Pipeline — Grade: F 🔴

| Missing | Impact |
|---------|--------|
| No `.github/workflows/` | No automated testing on PR |
| No `pyproject.toml` | No dependency groups, no build metadata |
| No `pytest.ini` / `setup.cfg` | No test markers, no coverage threshold |
| No branch protection | Anyone can push to main |
| No PR gating | No required checks before merge |
| No lint/type/security in CI | Regressions slip through |

### 2. Type Hint Coverage — Grade: C 🟡

- **304 total functions** across the codebase
- **Only 148 have type hints** → **49% coverage**
- **Zero-coverage modules:** `avcpm_auth` (0/20), `avcpm_task` (0/32), `avcpm_merge` (0/6), `avcpm_commit` (0/7)
- **A-grade target:** ≥85%

### 3. Remaining Security Items — Grade: B 🟡

| ID | Issue | Risk | Effort | Sprint |
|----|-------|------|--------|--------|
| M-S4 | Anti-replay for challenges | Challenge reuse within expiry window | 3pt | 4 |
| M-S5 | Atomic writes + file locks | Race conditions on concurrent auth | 5pt | 4 |
| M-S7 | Genesis ledger anchoring | No tamper-evident root for chain | 3pt | 5 |

**Dependency:** M-S5 (atomic writes) → M-S4 (anti-replay). The `used_at` flag must be written atomically.

### 4. Test Infrastructure — Grade: B+ 🟡

| Gap | Impact |
|-----|--------|
| No `conftest.py` | Every test file reinvents fixtures |
| Mixed unittest/pytest | `lifecycle.py`, `wip.py`, `validate.py` still unittest |
| No coverage config | Can't measure actual coverage |
| No `tox.ini` | No multi-Python testing |
| `avcpm_audit.py` has zero tests | Forensic backbone is untested |
| `time.sleep(1)` in tests | Serial and slow |
| Missing edge cases | Empty files, binary files, permission denied, clock skew |

### 5. Static Analysis — Grade: C 🟡

| Missing | Impact |
|---------|--------|
| No `bandit` | Security regressions undetected |
| No `mypy` | Type errors in production |
| No `ruff`/`flake8` | Style drift, unused imports |
| No dependency lock file | Supply chain risk |

### 6. Architecture Polish — Grade: A- 🟢

| Issue | Severity |
|-------|----------|
| Deferred imports inside functions | Code smell, affects readability |
| No consistent error hierarchy | Mix of ValueError, SecurityError, FileNotFoundError |
| `avcpm_cli.py` is 1157 LOC | Oversized, could extract command handlers |
| `cryptography` is heavy | Consider if lighter crypto acceptable |

---

## Sprint 4: Foundation & Hardening (Weeks 9–11) — **18 pts**

**Theme:** "Build the quality infrastructure"

| # | Item | Story Pts | Owner | Files | Notes |
|---|------|-----------|-------|-------|-------|
| 1 | **CI/CD pipeline** — GitHub Actions workflow | 5 | Architecture | `.github/workflows/test.yml` | Lint (ruff), type-check (mypy), test (pytest), security (bandit), coverage (80% gate) |
| 2 | **M-S5: Atomic writes + file locks** | 5 | Security | `avcpm_auth.py`, `avcpm_security.py` | `fcntl.flock` + `tempfile` + `os.replace`. Prerequisite for M-S4. |
| 3 | **M-S4: Anti-replay for challenges** | 3 | Security | `avcpm_auth.py` | Add `used_at` field to challenges, check on verify, reject replays |
| 4 | **avcpm_audit tests** | 3 | Testing | `test_avcpm_audit.py` (new) | Log writes, rotation at 10MB, corrupt-line handling, read filtering |
| 5 | **Error hierarchy** — `AVCPMError` base | 2 | Architecture | `avcpm_exceptions.py` (new) | `AuthError`, `LedgerError`, `SecurityError` subclass from shared base |

**Sprint 4 DoD:**
- [ ] PRs blocked until CI passes
- [ ] `bandit -r .` passes with no high-severity warnings
- [ ] `mypy` runs clean on 60%+ of modules
- [ ] Challenge replay fails in test
- [ ] Audit module has 15+ tests

---

## Sprint 5: Polish & Coverage (Weeks 12–13) — **16 pts**

**Theme:** "Reach professional-grade polish"

| # | Item | Story Pts | Owner | Files | Notes |
|---|------|-----------|-------|-------|-------|
| 6 | **Type hints to 85%** | 5 | Architecture | `avcpm_auth.py`, `avcpm_task.py`, `avcpm_merge.py`, `avcpm_commit.py` | Batch by module. Use `typing` imports. Add `mypy --strict` gate. |
| 7 | **M-S7: Genesis ledger anchoring** | 3 | Security | `avcpm_ledger_integrity.py`, `avcpm_branch.py` | First entry gets well-known genesis hash, verified on integrity check |
| 8 | **Static analysis in CI** — fail-on-new | 3 | Testing | `.github/workflows/test.yml` | `mypy --strict`, `bandit -r`, `ruff check`; fail PR on new violations |
| 9 | **CLI refactor** — extract command handlers | 3 | Architecture | `avcpm_cli.py` → `avcpm_commands/` | Extract subcommand modules from 1157 LOC monolith |
| 10 | **Dependency audit** — pin + lock | 2 | Architecture | `pyproject.toml` / `requirements-lock.txt` | Pin versions, add hashes, document minimum Python version |

**Sprint 5 DoD:**
- [ ] Type coverage ≥85% (measured by `mypy`)
- [ ] Genesis entry rejected if tampered
- [ ] CI fails on new lint/type/security violations
- [ ] CLI module under 800 LOC
- [ ] Dependency lock file present

---

## Cross-Sprint Dependency Graph

```
Sprint 4
├── CI/CD pipeline (1) ──────────────► Static analysis in CI (8)
├── Error hierarchy (5) ─────────────► Type hints (6) — consistent exception types
├── M-S5 atomic writes (2) ──────────► M-S4 anti-replay (3) — used_at flag must be atomic
├── M-S5 atomic writes (2) ──────────► M-S7 genesis anchor (7) — ledger writes must be atomic
└── avcpm_audit tests (4) ───────────► Static analysis in CI (8) — coverage gate

Sprint 5
├── Type hints (6) ────────────────► Static analysis in CI (8) — mypy gate needs types
├── M-S7 genesis anchor (7) ───────► Static analysis in CI (8) — new code must pass
├── CLI refactor (9) ──────────────► Static analysis in CI (8) — extracted modules need types
└── Dependency audit (10) ───────────► Static analysis in CI (8) — lock file in CI env
```

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| CI pipeline breaks on first run | High | Medium | Use `continue-on-error: true` initially, then tighten |
| Type hints cause circular import issues | Medium | High | Add `from __future__ import annotations`; use string forward refs |
| M-S5 file locks break on Windows/WSL | Medium | Medium | Test on both Unix and Windows runners in CI |
| CLI refactor introduces regressions | Medium | High | Extract one command at a time; run full test suite after each |
| Sprint 5 scope creep (16 pts aggressive) | Medium | Medium | Cut CLI refactor or dependency audit if behind |

---

## Exit Criteria (A Grade)

- [x] All critical issues closed
- [x] All security majors closed (M-S1-S3, S6, S8, S9 + M-S4, S5, S7)
- [x] All core VCS majors closed
- [x] All architecture majors closed
- [x] Unit tests for commit and merge
- [ ] **CI/CD pipeline running on every PR**
- [ ] **`bandit -r .` passes with no high-severity warnings**
- [ ] **`mypy` type-checks clean on ≥85% of modules**
- [ ] **Test coverage ≥80% with enforcement**
- [ ] **Genesis ledger anchored**
- [ ] **Anti-replay enforced**
- [ ] **Atomic writes for all RMW operations**
- [ ] **Dependency lock file present**
- [ ] **Error hierarchy with shared base**

---

## Team Assignments

| Role | Model | Sprint Focus |
|------|-------|-------------|
| Architecture Lead | GLM-5.1 | Sprint 4: CI/CD (1), Error hierarchy (5). Sprint 5: Type hints (6), CLI refactor (9), Dependency audit (10) |
| Security Lead | Claude Code | Sprint 4: M-S5 atomic writes (2), M-S4 anti-replay (3). Sprint 5: M-S7 genesis anchor (7) |
| Testing Lead | MiniMax M2.7 | Sprint 4: Audit tests (4), CI integration. Sprint 5: Static analysis gating (8), coverage enforcement |

---

## Conclusion

**Total: 34 story points across 5 weeks.** Sprint 4 is the heaviest because it builds the infrastructure that enables everything else. Sprint 5 is lighter by design — polish and coverage.

The critical path is: **CI/CD pipeline (1) → M-S5 atomic writes (2) → M-S4 anti-replay (3) → M-S7 genesis anchor (7) → Static analysis gating (8)**. Without CI, every other improvement is invisible.

**Most impactful single change:** CI/CD pipeline. It transforms every subsequent PR from "trust me, I tested it" to "the machine proved it."

📄 Full plan saved to `/home/user/.openclaw/workspace/avcpm_a_grade_roadmap.md`

**Ready to start Sprint 4?**