# AVCPM - AI-Native Version Control & Project Management

> 🎉 **Phase 1 Complete** - Core toolkit operational as of 2026-04-19

A lightweight, file-based version control and task management system designed for AI-assisted development workflows.

---

## Module Overview

| Script | Purpose | Key Commands |
|--------|---------|--------------|
| `avcpm_task.py` | Kanban-style task board | `create`, `move`, `list` |
| `avcpm_commit.py` | Commit artifacts with SHA256 checksums | `<task_id> <agent> <rationale> <files...>` |
| `avcpm_validate.py` | Verify staging checksums against ledger | validate, `--fix`, `--json` |
| `avcpm_status.py` | Unified status dashboard | sections: `--tasks`, `--ledger`, `--staging`, `--health` |
| `avcpm_merge.py` | Promote approved commits to production | `<commit_id>` |

---

## Quick Start (5 Commands)

```bash
# 1. Create a task
python avcpm_task.py create TASK-42 "Implement feature X" developer-agent

# 2. Move to in-progress
python avcpm_task.py move TASK-42 in-progress

# 3. Commit your work
python avcpm_commit.py TASK-42 dev-agent "Initial implementation" file.py

# 4. Validate checksums
python avcpm_validate.py

# 5. After review approval, merge to production
python avcpm_merge.py 20260419120000
```

---

## Command Reference

### `avcpm_task.py` - Task Board

```bash
# Create a new task in 'todo' column
python avcpm_task.py create <task_id> <description> [assignee]

# Move task between columns (todo|in-progress|review|done)
python avcpm_task.py move <task_id> <new_status>

# List all tasks by column
python avcpm_task.py list
```

### `avcpm_commit.py` - Commit Artifacts

```bash
python avcpm_commit.py <task_id> <agent_id> <rationale> <file1> [file2...]

# Example:
python avcpm_commit.py TASK-42 dev-agent "Fix null pointer" src/utils.py tests/test_utils.py
```

- Copies files to `.avcpm/staging/`
- Creates ledger entry in `.avcpm/ledger/<timestamp>.json`
- Calculates SHA256 checksums for each file

### `avcpm_validate.py` - Checksum Validation

```bash
# Validate all staging files against ledger
python avcpm_validate.py

# Fix mismatched checksums (updates ledger)
python avcpm_validate.py --fix

# JSON output for scripting
python avcpm_validate.py --json

# Quiet mode (summary only)
python avcpm_validate.py --quiet
```

### `avcpm_status.py` - Status Dashboard

```bash
# Show complete status (tasks + ledger + staging + health)
python avcpm_status.py

# Show specific sections
python avcpm_status.py --tasks      # Task board summary
python avcpm_status.py --ledger     # Recent commits
python avcpm_status.py --staging    # Files in staging
python avcpm_status.py --health     # System health check

# Machine-readable output
python avcpm_status.py --json
```

### `avcpm_merge.py` - Promote to Production

```bash
# Merge an approved commit (requires .avcpm/reviews/<commit_id>.review with "APPROVED")
python avcpm_merge.py <commit_id>
```

- Copies files from `.avcpm/staging/` to production (workspace root)
- Requires approval file to exist

---

## Project Structure

See `.avcpm/README.md` for detailed directory structure and workflow guide.

---

*AVCPM v1.0 - Phase 1 Complete*
