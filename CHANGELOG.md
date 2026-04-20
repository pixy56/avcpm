# AVCPM Changelog

## [Phase 1] - 2026-04-19

Initial release - Core toolkit complete.

### Added

- **`avcpm_task.py`** - Kanban task board with create/move/list operations
  - Columns: todo, in-progress, review, done
  - JSON-based task storage with status history
  
- **`avcpm_commit.py`** - Artifact commit with SHA256 checksums
  - Copies files to staging
  - Creates immutable ledger entries
  - Tracks agent, task, and rationale
  
- **`avcpm_validate.py`** - Checksum validation
  - Validates all staging files against ledger
  - `--fix` flag to update mismatched checksums
  - `--json` output for automation
  - Detects orphaned files and missing entries
  
- **`avcpm_status.py`** - Unified status dashboard
  - Task board summary
  - Ledger activity (last 10 commits)
  - Staging file listing
  - System health checks
  
- **`avcpm_merge.py`** - Production promotion
  - Merges approved commits to workspace root
  - Requires `APPROVED` review file
  - Copies from staging to production

### Directory Structure

- `.avcpm/tasks/{todo,in-progress,review,done}/` - Task board columns
- `.avcpm/ledger/` - Commit history (JSON)
- `.avcpm/staging/` - Staged artifacts
- `.avcpm/reviews/` - Review approvals

---

## Future Phases (Planned)

- Phase 2: Conflict resolution, branching strategies
- Phase 3: Hooks/plugins, remote sync
- Phase 4: Web UI, collaborative features
