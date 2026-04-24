# AVCPM Security Assessment: B+ → A Grade Roadmap

**Date:** 2026-04-24  
**Current Grade:** B+  
**Target Grade:** A  
**Assessor:** Subagent (security review)

---

## Executive Summary

AVCPM has made excellent progress through three security sprints. The core cryptographic foundation is strong (AES-GCM, PBKDF2 600k, RSA-2048 signatures, compare_digest). Path traversal defenses are comprehensive (validate_agent_id, O_NOFOLLOW, safe_join, sanitize_path). Audit logging with rotation is implemented.

**Remaining gap to A grade:** 3 missing items from the original plan (M-S4, M-S5, M-S7) plus documentation gaps (threat model, key management, incident response) and 1 critical bug in the merge module.

---

## 1. Current Security State (Verified)

### ✅ Implemented (Post-Sprint 3)

| Control | Status | Evidence |
|---------|--------|----------|
| **AES-GCM encryption** (M-S1) | ✅ | `avcpm_agent.py` — `_encrypt_data()` uses GCM with v2 format |
| **PBKDF2 600k iterations** (M-S2) | ✅ | `avcpm_agent.py` `ENCRYPTION_ITERATIONS = 600000` |
| **Timing-safe compare** (M-S3) | ✅ | `avcpm_auth.py` — `secrets.compare_digest()` on session tokens |
| **Anti-replay guard** | ⚠️ Partial | Challenge has 5-min expiry but NO reuse detection |
| **Cleanup guards** (M-S6) | ✅ | `cleanup_expired_sessions()`, `cleanup_expired_challenges()` |
| **O_NOFOLLOW** (M-S8) | ✅ | `avcpm_security.py` — `safe_open_nofollow()` with `os.O_NOFOLLOW` |
| **Audit logging** (M-S9) | ✅ | `avcpm_audit.py` — append-only with 10MB rotation, 5 backups |
| **Path traversal defense** | ✅ | `validate_agent_id` regex, `safe_join`, `sanitize_path`, symlink checks |
| **RSA 2048 signatures** | ✅ | `avcpm_agent.py` — PSS padding, SHA-256, PKCS8 |
| **Commit integrity chain** | ✅ | `avcpm_ledger_integrity.py` — SHA256 entry hashes + previous_hash linking |
| **Encryption at rest** | ✅ | Private keys encrypted by default, AES-256-GCM |
| **Challenge-response auth** | ✅ | `avcpm_auth.py` — RSA-signed challenges with nonce |
| **Session expiry** | ✅ | 60-minute TTL on sessions, auto-cleanup |
| **File permissions** | ✅ | `os.chmod(0o600)` on encrypted keys |
| **Adversarial test suite** | ✅ | `test_avcpm_security.py` + `test_sprint1_security.py` |

### ⚠️ Partially Implemented

| Control | Status | Issue |
|---------|--------|-------|
| **Anti-replay for challenges** (M-S4) | ⚠️ Partial | Challenges have 5-min expiry but no mechanism to prevent reuse of valid (non-expired) challenges |
| **Atomic writes for data files** (M-S5) | ⚠️ Missing | Session and challenge files written with plain `open("w")` — no mkstemp+rename or fcntl locks |
| **Genesis ledger anchoring** (M-S7) | ⚠️ Missing | First ledger entry has no external anchor to establish chain of trust |

### ❌ Missing

| Control | Status | Severity |
|---------|--------|----------|
| **Threat model documentation** | ❌ | High |
| **Key management guide** | ❌ | Medium |
| **Incident response procedures** | ❌ | Medium |
| **SECURITY.md** | ❌ | Low |

---

## 2. Remaining Security Gaps (Detailed)

### Gap 2.1: Challenge Replay Attack (M-S4)

**Risk Level:** Medium  
**CVE analog:** CWE-294 (Authentication Bypass by Capture-Replay)

**Current implementation flaw:**
```python
# avcpm_auth.py line 47-48
challenge = generate_challenge()
# ... stored to disk ...
```

The challenge is stored as JSON with a 5-minute expiry window. However:
1. **No nonce tracking** — there's no list of used challenges to prevent reuse
2. **No per-challenge counter** — the same agent could theoretically use a challenge multiple times within its 5-minute window
3. **Challenge file is readable by any user** — an attacker with filesystem access could grab a fresh challenge and replay it

**Attack scenario:**
1. Attacker reads `agent_challenges/<agent_id>.json` → gets `challenge` value
2. Attacker computes `AVCPM_AUTH:<agent_id>:<challenge>` and signs with stolen public key (if private key was exposed) or simply replays before expiry
3. If challenge is never cleared after first use, replay is possible

**Fix:**
- Add `used: False` field to challenge data
- Set `used = True` immediately upon verification in `verify_challenge_response()`
- Reject `used=True` challenges immediately
- Or better: clear challenge immediately upon successful auth (already done in `authenticate_agent()`), but add the `used` check for the TOCTOU window

### Gap 2.2: Atomic Writes + File Locks (M-S5)

**Risk Level:** Medium-High  
**CVE analog:** CWE-362 (Concurrent Execution using Shared Resource with Improper Synchronization)

**Current implementation flaw:**
```python
# avcpm_auth.py create_session():
with open(session_file, "w") as f:
    json.dump(session_data, f, indent=4)
```

Issues:
1. **Session/challenge files are not atomic** — if interrupted mid-write, file is corrupted
2. **No file locking** — concurrent agent writes can race
3. **Registry.json has same problem** — `_save_registry()` uses plain `open("w")`
4. **avcpm_task.py has partial mitigation** — uses `mkstemp` + rename (correct pattern)
5. **avcpm_commit.py and avcpm_merge.py** — ledger entries written with plain `open("w")`

**Attack scenario:**
1. Two agents commit simultaneously → race on registry.json → one write overwrites the other
2. System crash mid-write → corrupted JSON → AVCPM fails to parse → denial of service
3. Ledger entry is written partially → integrity chain has a corrupted entry

**Fix:**
- Use `tempfile.mkstemp()` in same directory + `os.rename()` pattern (already in `avcpm_task.py`)
- Add `fcntl.flock()` (Unix) for write locks on session/challenge files
- Apply to: `create_session()`, `create_challenge()`, `_save_registry()`, `commit()`, merge ledger writes

### Gap 2.3: Genesis Ledger Anchoring (M-S7)

**Risk Level:** Medium  
**CVE analog:** CWE-284 (Improper Access Control — trust anchor weakness)

**Current implementation flaw:**
The ledger chain starts with a "first" entry that has `previous_hash: null`. There's no way to verify that this first entry is genuine — it could be fabricated. The chain only protects *forward* integrity, not *initial* trust.

**Attack scenario:**
1. Attacker creates a fake "genesis" ledger entry with a valid (but attacker-controlled) key pair
2. Subsequent entries in the chain verify correctly against the fake genesis
3. No external verification exists to distinguish real from fake chain

**Fix:**
- Create a "genesis anchor" — an externally verifiable commitment at ledger creation:
  - Sign the genesis entry hash with a system/root key (not agent key)
  - Write genesis hash to an out-of-band channel (e.g., external storage, blockchain, or trusted server)
  - Store `genesis_signature` in the first ledger entry
  - Verify `genesis_signature` on every integrity check

### Gap 2.4: Merge Module Bug

**Risk Level:** Critical  
**CVE analog:** Unhandled variable reference → crash

**Found in `avcpm_merge.py` line ~147:**
```python
audit_log(EVENT_MERGE, merging_agent_id or "unknown", {
```

The variable `merging_agent_id` is used *before* it's defined (defined on line ~154). This is an `UnboundLocalError` crash on every merge audit log call.

### Gap 2.5: Missing Documentation

**Risk Level:** High (for A grade)

- **No threat model** — per CODE_REVIEW_SECURITY.md line 551: "No document describing what threats AVCPM protects against"
- **No key management guide** — no guidance on key backup, rotation, revocation
- **No incident response** — no procedures for compromised keys
- **No SECURITY.md** — per recommendations in CODE_REVIEW_SECURITY.md

---

## 3. Risk Analysis

### Threat Model Analysis

| Threat Actor | Capability | Current Defense | Remaining Risk |
|--------------|-----------|-----------------|----------------|
| **Local malicious user** | File system access on same host | O_NOFOLLOW, file permissions, validate_agent_id | Medium: can read session files, replay challenges within 5-min window |
| **Compromised agent key** | Stolen private key + valid session | RSA signatures, integrity chain | Low: chain detects tampering, but replay possible without M-S4 |
| **Concurrent agent writes** | Multiple agents writing simultaneously | Partial (task module) | Medium: race conditions on registry/session files |
| **Ledger chain forgery** | Attacker can create fake ledger | Integrity chain verification | Medium: genesis anchoring missing (M-S7) |
| **File corruption** | Crash/interrupt during writes | None for most files | Low-Medium: atomic writes missing (M-S5) |
| **Session hijacking** | Stolen session token | Session expiry, compare_digest | Low-Medium: compare_digest prevents timing attack but not token theft |
| **Symlink attacks** | Symlink to sensitive files | O_NOFOLLOW, validate_agent_id | Low: well defended |

### Priority Ranking of Remaining Items

| Priority | Item | Impact on A Grade | Effort |
|----------|------|-------------------|--------|
| **P0** | Fix merge crash (Gap 2.4) | Prevents correct merge audit logging | 15 min |
| **P1** | Challenge replay (M-S4) | Closes authentication gap | 1-2 hours |
| **P1** | Atomic writes (M-S5) | Prevents data corruption/race conditions | 2-3 hours |
| **P2** | Genesis anchoring (M-S7) | Completes integrity chain trust | 2-4 hours |
| **P2** | Threat model (DOC-1) | Required for A grade documentation | 2-3 hours |
| **P3** | Key management (DOC-2) | Operational security | 1-2 hours |
| **P3** | Incident response (DOC-3) | Operational security | 1-2 hours |
| **P3** | SECURITY.md (DOC-4) | Policy documentation | 30 min |

---

## 4. Security Roadmap: B+ → A Grade

### Sprint 0: Critical Fix (Immediate, 0.5 day)

**Goal:** Fix the merge crash bug

| Task | Details |
|------|---------|
| Fix `merging_agent_id` bug in `avcpm_merge.py` | Move variable definition before first use, or use `agent_id or commit_data.get("agent_id")` |

### Sprint 4: Anti-Replay + Atomic Writes (1-2 days)

**Goal:** Complete M-S4 and M-S5 from original plan

| Task | Details |
|------|---------|
| M-S4a: Add `used` field to challenge data | Update challenge JSON schema |
| M-S4b: Check `used` in `verify_challenge_response()` | Reject used challenges immediately |
| M-S4c: Clear challenge file after successful auth | Already partially done — make it unconditional |
| M-S5a: Implement `atomic_write(path, data)` helper | mkstemp + rename pattern |
| M-S5b: Apply to session/challenge files | `create_session()`, `create_challenge()` |
| M-S5c: Apply to registry.json | `_save_registry()` |
| M-S5d: Apply to ledger writes | `commit()`, merge ledger writes |
| M-S5e: Add fcntl.flock() for concurrent safety | Write lock on session/challenge files |
| M-S5f: Write tests for atomic writes | Unit tests for race conditions |

### Sprint 5: Genesis Anchoring + Documentation (1-2 days)

**Goal:** Complete M-S7 and create missing documentation

| Task | Details |
|------|---------|
| M-S7a: Add `genesis_signature` to first ledger entry | Sign genesis with a known root key |
| M-S7b: Add genesis verification to integrity chain | `verify_ledger_integrity()` checks genesis |
| M-S7c: Add M-S7 tests | Test genesis chain from creation |
| DOC-1: Write THREAT_MODEL.md | Document threats, assumptions, attack surfaces |
| DOC-2: Write KEY_MANAGEMENT.md | Key backup, rotation, revocation |
| DOC-3: Write INCIDENT_RESPONSE.md | Compromised key procedures |
| DOC-4: Write SECURITY.md | Policy, disclosure process |

### Sprint 6: Polish (0.5 day)

| Task | Details |
|------|---------|
| Run full test suite | All tests pass |
| Security audit re-run | Verify all gaps closed |
| Update CHANGELOG | Document security improvements |

---

## 5. Recommendations: Can Items Be Deferred?

### M-S4 (Anti-Replay for Challenges) — **DO NOT DEFER**

**Verdict:** Required for A grade. This is a genuine authentication gap.

**Why:** The challenge-response protocol's entire purpose is to prove possession of a private key in real-time. Without anti-replay, a captured challenge can be replayed by anyone with filesystem access during the 5-minute validity window. This undermines the core authentication mechanism.

**Defer risk:** An attacker with read access to `agent_challenges/` could replay a captured challenge. For a file-based auth system where all agents share the same filesystem, this is a real attack vector.

### M-S5 (Atomic Writes + File Locks) — **DO NOT DEFER**

**Verdict:** Required for A grade. This is a data integrity gap.

**Why:** AVCPM's core promise is traceability and integrity of the commit ledger. Without atomic writes, corrupted JSON files can:
1. Crash the system (DoS)
2. Create inconsistent state (two agents see different registry state)
3. Leave orphaned ledger entries that break the integrity chain

**Defer risk:** In multi-agent scenarios (which AVCPM is designed for), race conditions are likely. The task module already uses mkstemp+rename but the rest doesn't — inconsistency creates a false sense of security.

### M-S7 (Genesis Ledger Anchoring) — **DEFERRABLE** (with conditions)

**Verdict:** Can be deferred to A+ grade. It's a nice-to-have for current threat model.

**Why:** In the current deployment model:
- All agents share a single filesystem
- The first ledger entry is created during initial setup
- There's no mechanism to inject arbitrary genesis entries without access to that setup phase

**The chain still provides strong protection** against post-creation tampering (which is the primary threat). Genesis forgery requires access to the initial setup environment, which is already a highly privileged attack.

**Conditions for deferral:**
- Document the trust assumption explicitly in the threat model
- Note that genesis anchoring should be added when AVCPM is deployed across trust boundaries
- The integrity chain still catches any tampering after the first entry

**If deferred:** It blocks the "A+" grade (full zero-trust chain of trust) but not "A" grade.

### Documentation Items — **REQUIRED for A grade**

**Verdict:** All documentation items are mandatory for A grade. AVCPM's own CODE_REVIEW_SECURITY.md explicitly lists threat model and security documentation as Priority 4 requirements, and grading rubrics require threat model completeness.

---

## 6. Summary: What's Needed for A Grade

| Category | Items Needed |
|----------|-------------|
| **Code fixes** | M-S4 (anti-replay), M-S5 (atomic writes), merge crash fix |
| **Integrity** | M-S7 (genesis anchoring) — deferrable with documented assumption |
| **Documentation** | THREAT_MODEL.md, KEY_MANAGEMENT.md, INCIDENT_RESPONSE.md, SECURITY.md |
| **Testing** | Tests for anti-replay, atomic writes, genesis verification |

**Total effort estimate:** 2-3 days for code + 1-2 days for documentation

**A-grade checklist:**
- [ ] All challenges track usage state (no replay)
- [ ] All data files use atomic writes
- [ ] All concurrent writes use file locks
- [ ] Merge audit log crash fixed
- [ ] Genesis entry verified via integrity chain
- [ ] Threat model document created and reviewed
- [ ] Key management procedures documented
- [ ] Incident response procedures documented
- [ ] SECURITY.md created
- [ ] All new features tested with adversarial test cases
- [ ] Full test suite passes

---

*Assessment complete. All findings verified against source code at `/tmp/avcpm`.*
