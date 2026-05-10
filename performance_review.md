# AVCPM Performance Review

## 1. Algorithmic Complexity

### O(n²) or Worse Operations

- **`avcpm_task.py: get_dependents()`** — Loads *all* tasks via `get_all_tasks()` and scans every task’s dependency list. Called frequently by dependency validation. For dense dependency graphs this approaches O(n²).

- **`avcpm_task.py: would_create_cycle()`** — Uses a recursive DFS `reaches()` that re-walks the graph from the candidate dependency. In the worst case it traverses the entire task graph on every add. With deep chains this is O(V+E) per operation, but since `get_dependents()` is also called inside lifecycle checks, the combined cost is super-linear.

- **`avcpm_status.py: check_system_health()`** — Cross-references staging files against ledger entries with nested loops. It extracts `tracked_names` by iterating every change in every ledger entry, then subtracts sets. The inner extraction loop is O(ledger_entries × avg_changes_per_entry × staging_files).

- **`avcpm_validate.py: fix_mismatches()`** — For every failed validation result, it reloads *all* ledger entries via `load_ledger_entries()` and scans them again. If 10 files fail on a repo with 500 commits, that’s 5,000 JSON parses.

### Redundant Work

- **`avcpm_commit.py`** — The file list is sanitized twice with identical `sanitize_path()` loops (lines ~107 and ~116). Waste of CPU and confusing.

- **`avcpm_rollback.py: _get_commits_in_branch()`** — Parses JSON for every commit file just to sort by `commit_id`, but `commit_id` is already the filename. Could sort filenames directly and only parse the target commits.

---

## 2. I/O Patterns

### Redundant Disk Reads (No Caching)

Almost every module re-reads JSON files from disk with **zero in-memory caching**:

- **Branch metadata** — `_is_ancestor()` loads parent metadata files from disk at each depth level. Deep branch trees = many disk reads.
- **Task data** — `load_task()`, `get_all_tasks()`, `get_dependents()` read task files repeatedly within the same operation flow.
- **Ledger entries** — `file_history()`, `blame()`, `get_ledger_entries()`, `verify_ledger_integrity()` all load and parse commit JSONs every time they run.
- **Agent registry** — `_load_registry()` reads the full agent registry on every agent lookup.
- **WIP registry** — `_load_registry()` reads the entire claims file on every single claim/release/check operation.

### Missing Caching Opportunities

- Task boards, branch metadata, and agent registries are small enough to cache in memory for the duration of a CLI invocation.
- Ledger entries are read far more often than they change; a simple LRU cache on `_load_commit()` would drastically speed up `blame`, `diff`, and `file_history`.
- The WIP registry is read-modified-written on every claim. With no caching, this is a disk read+write per file claim.

---

## 3. Memory Usage

### Unbounded Growth

- **`avcpm_wip.py`** — WIP registry is a single JSON file (`wip_registry.json`). As claim count grows, every `_load_registry()` / `_save_registry()` loads/rewrites the entire structure. Memory usage is O(total_claims) per operation.
- **`avcpm_agent.py`** — Agent registry is a single JSON file. Same unbounded growth pattern.
- **`avcpm_task.py: get_all_tasks()`** — Loads every task file into memory. On a board with thousands of tasks, this is a large spike.
- **`avcpm_ledger_integrity.py: verify_ledger_integrity()`** — Loads every commit in a branch into memory simultaneously. A branch with 10,000 commits = 10,000 parsed JSON objects in RAM.
- **`avcpm_validate.py: load_ledger_entries()`** — Loads the entire ledger directory into memory.

### Large In-Memory Structures

- **`avcpm_conflict.py: merge_three_way()`** — For a file of N lines, it holds `base_lines`, `a_lines`, `b_lines`, and `merged_lines` simultaneously in memory (4× file size). For multi-MB files this is a problem.
- **`avcpm_rollback.py: create_backup()`** — `_copy_directory_tree()` traverses entire branch staging + ledger trees. Large repos = large memory footprint during tree walk.

### Memory Leaks (none detected)
No explicit leaks found, but the lack of streaming/chunked processing means memory pressure grows with repo size.

---

## 4. Concurrency

### Race Conditions (No File Locking Anywhere)

The entire codebase assumes single-process access. Multiple agents will corrupt state:

- **`avcpm_wip.py`** — Two agents claiming files simultaneously both read the registry, modify their copy, and write. Last write wins; one claim is silently lost.
- **`avcpm_task.py`** — `move_task()` uses `shutil.move()` between columns with no lock. Two moves of the same task can leave the task in both columns or neither.
- **`avcpm_commit.py`** — Ledger writes (`ledger_path` JSON file) are not atomic. Concurrent commits to the same branch can overwrite each other.
- **`avcpm_auth.py`** — Session and challenge files are read-modified-written with no locking.
- **`avcpm_branch.py`** — Branch metadata updates (rename, delete) are not atomic.
- **`avcpm_rollback.py`** — Auto-backup and destructive `reset_hard()` / `rollback()` operations interleave reads and writes with no atomicity guarantee.

### Blocking Operations

- All file I/O is synchronous and blocking. The CLI has no async I/O or threading.
- `detect_conflicts()` during merge blocks the entire merge until complete.

---

## 5. Scalability Limits

| Component | Breaks At | Why |
|-----------|-----------|-----|
| **WIP Registry** | ~1,000–5,000 claims | Single JSON file; rewrite latency dominates |
| **Agent Registry** | ~1,000 agents | Same single-file bottleneck |
| **Task Board** | ~2,000 tasks | `get_all_tasks()` loads entire board into RAM; `get_dependents()` is O(n²) |
| **Branch Ledger** | ~5,000 commits/branch | `verify_ledger_integrity()` and `file_history()` load all commits into memory |
| **Three-way merge** | ~10 MB files | `merge_three_way()` loads entire file contents as line lists (4× memory) |
| **Health check** | ~1,000 staging files | Nested ledger/staging cross-reference loops blow up |
| **Diff / Blame** | ~1,000 commits | `file_history()` scans every branch + every commit with no index |
| **Backup** | Large repo trees | `_copy_directory_tree()` copies everything; time and disk scale linearly with repo size |

### Branch Operations

- `_is_ancestor()` walks the ancestry chain by reading metadata files from disk. For a branch tree 50 levels deep, that’s 50 disk reads just to check ancestry.
- `delete_branch()` scans *all other branches’ ledgers* to check for unmerged commits. With many branches, this is expensive.

---

## 6. Benchmarking Gaps

The project has **zero benchmarks**. The following should be measured:

1. **Large ledger scan** — Time to run `verify_ledger_integrity()` on branches with 1k, 10k, 100k commits.
2. **Task board scale** — Time for `get_all_tasks()`, `get_dependents()`, and `move_task()` with 1k–10k tasks.
3. **Concurrent claims** — Measure race-condition rate with 10 parallel agents claiming files.
4. **Merge performance** — Time for `detect_conflicts()` and `merge_three_way()` on branches with 100+ modified files and files sized 1KB–10MB.
5. **Diff / blame throughput** — Time for `file_history()` and `blame()` on a file touched by 100+ commits across 10+ branches.
6. **Backup latency** — Time and disk I/O for `create_backup()` on a 1GB repo tree.
7. **Registry rewrite latency** — Time to claim/release WIP files as registry grows from 0 → 10k entries.
8. **Memory profiling** — Peak RSS during `merge_three_way()`, `create_backup()`, and `verify_ledger_integrity()`.

---

## 7. Recommendations (Prioritized)

### 🔴 Critical — Fix First

1. **Add file locking** — Use `fcntl.flock` (Unix) or a lockfile for all read-modify-write operations, especially WIP registry, task moves, and ledger commits. Without this, multi-agent usage is unsafe.
2. **Remove duplicate `sanitize_path` in `avcpm_commit.py`** — Merge the two identical loops into one.
3. **Make ledger writes atomic** — Write to a temp file, then `os.rename()` into place. Prevents half-written commits on crash or race.

### 🟠 High — Major Wins

4. **Shard WIP and agent registries** — Instead of one monolithic JSON file, store one claim/agent per file (like tasks) or use a small SQLite DB. Eliminates O(n) rewrite cost.
5. **Add an in-memory LRU cache for `_load_commit()` and `load_task()`** — Most CLI operations read the same files multiple times. A simple cache would cut I/O by 50–80%.
6. **Optimize `file_history()` and `blame()`** — Build an index (e.g., `file_index.json` mapping `filepath → [commit_ids]`) updated at commit time, instead of scanning all branches and commits at query time.
7. **Stream `merge_three_way()`** — Use a line-generator approach or chunk large files. For files >1MB, fall back to a file-level merge instead of loading all lines into RAM.

### 🟡 Medium — Good Hygiene

8. **Optimize `_get_commits_in_branch()`** — Sort filenames directly; only parse JSON for commits you actually need.
9. **Optimize `fix_mismatches()`** — Build a `staging_path → ledger_file` index once, instead of reloading all ledger entries per failed result.
10. **Add chunked reading in `_calculate_file_hash()`** — Already uses 4KB blocks (good), but ensure all hash functions are consistent.
11. **Lazy-load in `check_system_health()`** — Don’t load 100 ledger entries and then iterate all staging files in nested loops. Use sets/dicts for O(1) lookups.

### 🟢 Low — Nice to Have

12. **Add async I/O or threading for backup operations** — `_copy_directory_tree()` can parallelize file copies.
13. **Add benchmark suite** — Use `pytest-benchmark` or `timeit` to track the metrics in section 6 and fail CI on regressions.
14. **Add a commit-graph index** — For deep branch trees, precompute ancestry so `_is_ancestor()` is O(1) lookup instead of O(depth) disk reads.

---

*Review completed. 17 source files analyzed. No tests were reviewed.*
