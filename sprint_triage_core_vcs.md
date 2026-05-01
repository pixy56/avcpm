# AVCPM Core VCS Sprint Triage Plan

> **Reviewer:** Core VCS Lead (Qwen 3.6:35b)  
> **Date:** 2026-04-24  
> **Scope:** C5, M-V1, M-V2, M-V3, M-V4, M-V5 only  
> **Sprint Capacity:** S1=3wks (security+critical), S2=3wks (arch+core VCS), S3=2wks (testing+cleanup)

---

## 1. Priority Queue

Priority = **data-loss risk** × **correctness impact** × **(complexity weight)**.  
Complexity weight: trivial=1, low=2, medium=3, high=4.

| Priority | ID  | Title                                    | Files to Change                            | Data-Loss | Correctness | Complexity | Score |
|----------|-----|------------------------------------------|--------------------------------------------|-----------|-------------|------------|-------|
| P0       | M-V2| Rollback reads file after deleting it    | `avcpm_rollback.py:217` (`unstage()`)     | HIGH      | HIGH        | medium(3)  | 36    |
| P1       | M-V3| Merge bypasses commit metadata           | `avcpm_merge.py` (merge function body)     | MEDIUM    | HIGH        | medium(3)  | 18    |
| P2       | M-V4| Staging files collide by basename        | `avcpm_commit.py:128` (staging path logic) | HIGH      | HIGH        | low(2)     | 16    |
| P3       | C5 | Commit ID collisions (sec-resolution)    | `avcpm_commit.py:131` (commit_id line)    | MEDIUM    | HIGH        | low(2)     | 12    |
| P4       | M-V5| Blame is trivially wrong                 | `avcpm_commit.py` + new blame data fields  | LOW       | MEDIUM      | medium(3)  | 6     |
| P5       | M-V1| Missing shutil import in avcpm_merge.py  | `avcpm_merge.py` (top imports)             | LOW       | HIGH        | trivial(1) | 2     |

---

## 2. Sprint Assignments

### Sprint 1 (Security + Critical Correctness) — 3 weeks

| Issue | Fix Description                                          | Complexity | Story Points |
|-------|----------------------------------------------------------|------------|-------------|
| M-V1  | Add `import shutil` at top of `avcpm_merge.py`          | trivial    | 1           |
| C5    | Append nanosecond + 4-char UUID suffix to commit_id     | low        | 2           |
| M-V2  | Fix rollback: do NOT call `unstage()` before restoring; save staging data before any deletion | medium | 5 |

**Rationale:** Sprint 1 must lock down critical data-safety bugs. M-V1 is a 30-second fix that unblocks all merge work. C5 is foundational — no higher-order fixes are trustworthy without deterministic commit IDs. M-V2 is the highest-scored issue: rollback silently corrupts state when `unstage()` has already removed staging files that `rollback()` later tries to read.

### Sprint 2 (Architecture + Core VCS) — 3 weeks

| Issue | Fix Description                                          | Complexity | Story Points |
|-------|----------------------------------------------------------|------------|-------------|
| M-V4  | Use `{base}/{relpath}` in staging dir instead of basename | low        | 3           |
| M-V3  | Create ledger entry on merge (new commit record with merge metadata, parent hashes) | medium | 5      |

**Rationale:** M-V4 is the structural fix for staging — without it, merges that touch files with colliding basenames silently overwrite data. M-V3 preserves chain integrity for merges so the ledger is a true history graph.

### Sprint 3 (Testing + Cleanup) — 2 weeks

| Issue | Fix Description                                          | Complexity | Story Points |
|-------|----------------------------------------------------------|------------|-------------|
| M-V5  | Add per-file blame metadata (`author`, `timestamp`, `parent_commit_id`) to `commit_meta` → wire into blame output | medium | 3    |

**Rationale:** Blame is a useful-but-not-critical feature. Its fix requires schema changes to `avcpm_commit.py` commit meta format plus a blame implementation/fix. Can be deferred to the cleanup sprint.

---

## 3. Dependency Graph

```
M-V1 (shutil import)
  │
  ├─→ M-V3 (merge metadata)  ← needs working shutil.copy2 in merge()
  │
  └─→ (merge tests)

C5 (commit ID uniqueness)
  │
  ├─→ M-V3 (merge metadata)  ← needs deterministic commit IDs for ledger entries
  │
  ├─→ M-V4 (staging path)    ← commit metadata references staging_path by name
  │
  └─→ (commit tests)

M-V4 (staging path collision fix)
  │
  ├─→ M-V3 (merge metadata)  ← merge reads staging paths from commit data
  │
  └─→ (merge tests)

M-V2 (rollback read-after-delete)
  │
  └─→ (rollback tests)
       ▲
       │ independent of other Core VCS fixes (uses staging paths as-is)
       │
M-V5 (blame metadata)
       │
       └─→ (blame tests)
```

**Critical path:** `M-V1 → M-V4 → M-V3` (3 sequential dependencies spanning all three sprints).  
**Parallel path:** `C5` (Sprint 1, no dependents block it).  
**Independent:** `M-V2` (fix its own bug in isolation, test in isolation).  
**Independent:** `M-V5` (deferred to Sprint 3, no blockers).

---

## 4. Per-Fix Detailed Notes

### M-V1 — Missing `shutil` import (Sprint 1, 1pt)

**What:** `avcpm_merge.py:108` calls `shutil.copy2(staging_file, dest_file)` but the file has no `import shutil`. This causes an `AttributeError` at runtime whenever merge actually copies a file.

**Fix:** Add `import shutil` to the top of `avcpm_merge.py` alongside existing imports.

**Files:** `avcpm_merge.py` — line ~8, after `import os`, `import sys`, `import json`.

---

### C5 — Commit ID collisions (Sprint 1, 2pts)

**What:** `avcpm_commit.py:131` uses `datetime.now().strftime("%Y%m%d%H%M%S")` — second-resolution timestamps. Any two commits within the same second produce identical `commit_id`s, which overwrite each other in the ledger directory and break the integrity hash chain.

**Fix:** Replace the timestamp with a nanosecond-precision ID plus a short UUID suffix:
```python
import uuid
nanosec_part = datetime.now().strftime("%Y%m%d%H%M%S%f")[:20]  # 20 chars: YYYYMMDDHHMMSSfff
short_id = str(uuid.uuid4())[:4]
commit_id = f"{nanosec_part}_{short_id}"  # e.g., "20260424005500123456_a3f7"
```

**Files:** `avcpm_commit.py` — change the `commit_id = ...` line (~line 131). Add `import uuid` to imports.

---

### M-V2 — Rollback reads file after deleting it (Sprint 1, 5pts)

**What:** When `unstage(commit_id)` is called on the branch being rolled back from, it removes staging files. Later, `rollback(commit_id)` tries to read the **parent** commit's staging copy via `_get_file_at_commit()` — but that parent's staging file was also deleted by `unstage()`. Result: rollback silently restores nothing, or restores stale/missing data.

**Root cause:** The rollback flow doesn't account for the case where `unstage()` has been called on the source branch. Staging files that were already unstaged are gone.

**Fix:** In `rollback()`, add a guard: before proceeding, check whether any parent staging files still exist. If they don't, check the backup (created by `_backup_before_destructive`) and restore from there. Alternatively, save parent staging data into `result["files_restored"]` entries before any deletion occurs, or use a "read-and-buffer" pattern.

**Concrete approach:**
1. Before any destructive ops in `rollback()`, walk all parent staging files and copy them into a temp buffer in the backup dir.
2. If the parent staging file no longer exists (was deleted), fall back to the backup copy.
3. Update `rollback()` and `unstage()` in `avcpm_rollback.py` so `unstage()` preserves a backup of files it removes.

**Files:** `avcpm_rollback.py` — `rollback()` (~line 170), `unstage()` (~line 250), `_backup_before_destructive()` helper.

**Tests:** Update `test_avcpm_rollback.py` — add scenario: call `unstage()` on branch A, then `rollback()` on same branch; verify files restore from backup.

---

### M-V3 — Merge bypasses commit metadata (Sprint 2, 5pts)

**What:** `avcpm_merge.py` copies files from staging to production but **never creates a new ledger entry** for the merge. The commit history has a gap: the merge's file changes are in production but have no corresponding commit record, no integrity hash, and no parent linkage.

**Fix:** After the file-copy loop in `merge()`, create a new ledger entry:
1. Generate a new `commit_id` (respects C5 fix from Sprint 1).
2. Build `commit_meta` with: `rationale="merge: <source_branch> → <target_branch>"`, parent hash = latest commit in target branch + source commit hash, agent_id = merging agent.
3. Sign the entry, calculate entry hash, write to the **target** branch's ledger.
4. Mark source branch as merged (already done — keep that).

**Files:** `avcpm_merge.py` — add after the file-copy loop (~line 115), before the lifecycle hook:
- New commit metadata construction
- Ledger path for target branch
- Sign + hash + write

**Tests:** `test_avcpm_merge.py` — new test file. Test cases:
- `test_merge_creates_ledger_entry` — verify new entry exists in target ledger after merge
- `test_merge_preserves_hash_chain` — verify target branch integrity hash chain includes merge commit
- `test_merge_bypass_fails_integrity_check` — before fix: verify integrity check passes (post-fix: verify no integrity violation from gaps)

---

### M-V4 — Staging files collide by basename (Sprint 2, 3pts)

**What:** `avcpm_commit.py:128` uses `os.path.basename(filepath)` for the staging path. Two files from different subdirectories with the same basename collide — the later one silently overwrites the earlier one.

Example: `src/config/settings.py` and `test/config/settings.py` both stage as `settings.py`.

**Fix:** Use the relative path from the working directory as the staging filename:
```python
rel_path = os.path.relpath(filepath, os.getcwd())
staging_path = os.path.join(staging_dir, rel_path)  # preserves directory structure
safe_makedirs(staging_path, base_dir, exist_ok=True)  # create parent dirs
```

**Files:** `avcpm_commit.py` — change `staging_path` construction (~line 128) and add a `safe_makedirs` call for parent directories.

**Tests:** `test_avcpm_commit.py` — add test: commit two files with same basename in different dirs, verify both appear in staging.

---

### M-V5 — Blame is trivially wrong (Sprint 3, 3pts)

**What:** `avcpm_commit.py` commit metadata has no per-file author/timestamp tracking. The blame output (whatever it currently does) has no data to work with — every line is attributed to the same last committer or to nothing at all.

**Fix:** Add blame-eligible fields to each change entry in commit metadata:
```python
"changes": [{
    "file": filepath,
    "checksum": checksum,
    "staging_path": staging_path,
    "blame_author": agent_id,
    "blame_timestamp": timestamp,
    "blame_commit": commit_id  # parent commit for line attribution
}]
```

Wire the blame data into the blame output function (likely in a separate blame module or a `avcpm_diff.py` extension).

**Files:** `avcpm_commit.py` — add fields to `commit_meta["changes"]` entries (~line 135). Possibly new `avcpm_blame.py` or add blame method to `avcpm_diff.py`.

**Tests:** `test_avcpm_blame.py` (new) — verify blame attribution for multi-commit file history.

---

## Summary

```
Sprint 1 (3 wks):  M-V1 (1pt) + C5 (2pt) + M-V2 (5pt)    = 8pts  | security + critical
Sprint 2 (3 wks):  M-V4 (3pt) + M-V3 (5pt)                = 8pts  | architecture + core VCS
Sprint 3 (2 wks):  M-V5 (3pt)                              = 3pts  | testing + cleanup
```

**Key risk:** The `M-V1 → M-V4 → M-V3` dependency chain means we can't do meaningful merge testing until Sprint 2. Sprint 1 merge work is limited to `shutil` import + unit-test stubs that mock the actual file-copy path.
