# AVCPM - AI-Native Version Control & Project Management

> **Version 3.0.0** - A lightweight, file-based version control and task management system designed for AI-assisted development workflows.

## Overview

AVCPM provides a complete version control and project management solution specifically built for AI agents to collaborate on codebase evolution. It offers:

- **Intent-Based Versioning**: Captures *why* a change was made, not just *what* changed
- **Task-Driven Development**: Kanban-style task board linked directly to commits
- **Built-in Security**: Challenge-response authentication, symlink-safe file operations, and SHA256 integrity verification
- **Review Workflow**: Structured code review process with approval gates
- **Branch Management**: Feature workspaces with conflict detection and resolution

## Features

| Feature | Description |
|---------|-------------|
| 📝 **Task Board** | Kanban columns (todo, in-progress, review, done) with dependency tracking |
| 🔒 **Secure Commits** | SHA256 checksums + challenge-response agent authentication |
| 🌿 **Branching** | Feature workspaces with conflict detection and auto-merge |
| 👀 **Code Review** | Structured review process with approval gates |
| 🔄 **Rollback** | Soft/hard resets, backup creation and restoration |
| 📊 **Status Dashboard** | Unified view of tasks, commits, staging, and system health |
| ⚡ **WIP Tracking** | File claiming to prevent concurrent modification conflicts |
| 🔐 **Security** | Symlink-safe operations, path traversal protection, agent identity verification |

## Installation

### Requirements

- Python 3.9 or higher
- `cryptography` library (for agent authentication)

### Setup

Clone the repository:

```bash
git clone https://github.com/pixy56/avcpm.git
cd avcpm
```

Install dependencies:

```bash
pip install cryptography
```

For development, install pytest:

```bash
pip install pytest
```

## Quick Start

```bash
# Create a task
python avcpm_cli.py task create TASK-42 "Implement feature X" developer-agent

# Move to in-progress
python avcpm_cli.py task move TASK-42 in-progress

# Claim files for editing (WIP tracking)
python avcpm_cli.py wip claim src/feature.py

# Commit your work
python avcpm_cli.py commit TASK-42 dev-agent "Initial implementation" src/feature.py

# Validate checksums
python avcpm_cli.py validate

# Check status
python avcpm_cli.py status

# After review approval, merge to production
python avcpm_cli.py merge <commit_id>
```

## Command Reference

### Unified CLI

All AVCPM commands are available through the unified CLI:

```bash
python avcpm_cli.py <command> [args...]
```

### Task Management (`task`)

```bash
# Create a new task
python avcpm_cli.py task create <task_id> <description> [assignee]

# Move task between columns (todo|in-progress|review|done)
python avcpm_cli.py task move <task_id> <new_status>

# List all tasks by column
python avcpm_cli.py task list

# Dependency management
python avcpm_cli.py task deps add <task_id> <dependency_task_id>
python avcpm_cli.py task deps remove <task_id> <dependency_task_id>
python avcpm_cli.py task deps show <task_id>
```

### Branch Management (`branch`)

```bash
# Create a feature branch
python avcpm_cli.py branch create feature-x

# List all branches
python avcpm_cli.py branch list

# Switch to a branch
python avcpm_cli.py branch switch feature-x

# Delete a branch
python avcpm_cli.py branch delete feature-x
```

### Commit & Validation (`commit`, `validate`)

```bash
# Commit files to staging with SHA256 checksums
python avcpm_cli.py commit <task_id> <agent_id> <rationale> <file1> [file2...]

# Validate all staging files against ledger
python avcpm_cli.py validate

# Fix mismatched checksums (updates ledger)
python avcpm_cli.py validate --fix

# JSON output for automation
python avcpm_cli.py validate --json
```

### Code Review & Merge (`merge`)

```bash
# Merge an approved commit to production
python avcpm_cli.py merge <commit_id>
```

Note: Merging requires an approval file at `.avcpm/reviews/<commit_id>.review` containing "APPROVED".

### Diff & History (`diff`)

```bash
# Show differences between commits
python avcpm_cli.py diff <commit_id_1> <commit_id_2>

# Show commit details
python avcpm_cli.py diff show <commit_id>

# View commit log
python avcpm_cli.py diff log

# Show file history with blame
python avcpm_cli.py diff blame <file_path>
```

### Conflict Resolution (`conflict`)

```bash
# Detect conflicts between branches
python avcpm_cli.py conflict detect

# List open conflicts
python avcpm_cli.py conflict list

# Resolve a conflict
python avcpm_cli.py conflict resolve <file_path> --resolution [ours|theirs|manual]
```

### Rollback & Recovery (`rollback`)

```bash
# Rollback to a specific commit
python avcpm_cli.py rollback <commit_id>

# Unstage files
python avcpm_cli.py rollback unstage <file1> [file2...]

# Soft reset (keep changes)
python avcpm_cli.py rollback reset-soft <commit_id>

# Hard reset (discard changes)
python avcpm_cli.py rollback reset-hard <commit_id>

# Backup management
python avcpm_cli.py rollback backup create
python avcpm_cli.py rollback backup list
python avcpm_cli.py rollback backup restore <backup_id>
```

### WIP Tracking (`wip`)

```bash
# Claim a file for editing
python avcpm_cli.py wip claim <file_path>

# Release a file
python avcpm_cli.py wip release <file_path>

# Release all your claims
python avcpm_cli.py wip release-all

# List all claims
python avcpm_cli.py wip list

# Check for conflicts
python avcpm_cli.py wip conflicts
```

### Status & Health (`status`)

```bash
# Show complete status (tasks + ledger + staging + health)
python avcpm_cli.py status

# Show specific sections
python avcpm_cli.py status --tasks      # Task board summary
python avcpm_cli.py status --ledger     # Recent commits
python avcpm_cli.py status --staging    # Files in staging
python avcpm_cli.py status --health     # System health check

# Machine-readable output
python avcpm_cli.py status --json
```

### Agent Identity (`agent`)

```bash
# Create an agent identity
python avcpm_cli.py agent create <agent_id> [--public-key <key_file>]

# List registered agents
python avcpm_cli.py agent list

# Show agent details
python avcpm_cli.py agent show <agent_id>
```

## Project Structure

```
.
├── avcpm_cli.py               # Unified CLI entry point
├── avcpm_task.py             # Task board management
├── avcpm_commit.py            # Commit artifacts with SHA256 checksums
├── avcpm_validate.py          # Checksum validation
├── avcpm_status.py            # Status dashboard
├── avcpm_merge.py             # Production promotion
├── avcpm_branch.py            # Branch management
├── avcpm_diff.py              # Diff and history tracking
├── avcpm_conflict.py          # Conflict detection and resolution
├── avcpm_rollback.py          # Rollback and recovery operations
├── avcpm_wip.py               # Work-in-progress tracking
├── avcpm_agent.py             # Agent identity management
├── avcpm_auth.py              # Challenge-response authentication
├── avcpm_security.py          # Safe file operations
├── avcpm_lifecycle.py         # Ledger lifecycle management
├── avcpm_ledger_integrity.py  # Ledger integrity verification
├── .avcpm/                    # AVCPM data directory
│   ├── tasks/                 # Kanban board columns
│   │   ├── todo/
│   │   ├── in-progress/
│   │   ├── review/
│   │   └── done/
│   ├── ledger/                # Commit history (JSON)
│   ├── staging/               # Staged artifacts
│   ├── reviews/               # Review approvals
│   ├── branches/              # Branch workspaces
│   ├── backups/               # Automatic backups
│   ├── conflicts/             # Conflict markers
│   ├── agent_challenges/      # Authentication challenges
│   └── agent_sessions/        # Active agent sessions
├── test_*.py                  # Test suites
├── AGENTS.md                  # Agent workspace guide
├── SOUL.md                    # Project philosophy
├── AVCPM.md                   # Quick reference
├── AVCPM_DESIGN.md            # System design document
└── README.md                  # This file
```

## Security Features

AVCPM includes comprehensive security measures:

### Authentication & Identity
- **Challenge-Response**: Agents must authenticate using cryptographic challenges
- **Session Management**: Sessions expire after 60 minutes
- **Agent Identity**: Public key verification for agent actions

### File System Security
- **Symlink-Safe Operations**: All file operations verify symlinks point within allowed directories
- **Path Traversal Protection**: Prevents `../` attacks and directory escape attempts
- **Atomic Operations**: File writes use temporary files and atomic moves

### Data Integrity
- **SHA256 Checksums**: Every commit includes file checksums for verification
- **Ledger Integrity**: Automatic verification of ledger consistency
- **Immutable History**: Commit entries are timestamped and signed

## Testing

Run the test suite with pytest:

```bash
# Run all tests
pytest test_avcpm_*.py -v

# Run specific module tests
pytest test_avcpm_cli.py -v
pytest test_avcpm_task.py -v
pytest test_avcpm_branch.py -v
pytest test_avcpm_conflict.py -v
pytest test_avcpm_lifecycle.py -v

# Run integration tests
python run_integration_tests.py
```

## Module Dependencies

The `cryptography` library is required for agent authentication features:

```bash
pip install cryptography
```

All other dependencies use Python standard library only.

## Version History

### Phase 1 (v1.0.0) - 2026-04-19
- Core toolkit: tasks, commits, validation, status, merge
- SHA256 checksums for artifact integrity
- Kanban task board with JSON storage

### Phase 2 (v2.0.0)
- Branch management and workspaces
- Conflict detection and resolution
- Diff and history tracking

### Phase 3 (v3.0.0) - Current
- Rollback and recovery operations
- WIP tracking with file claiming
- Agent authentication system
- Security module with safe file operations
- Ledger integrity verification
- Unified CLI (`avcpm_cli.py`)

## Documentation

- **[AGENTS.md](AGENTS.md)** - Guide for AI agents working in this workspace
- **[SOUL.md](SOUL.md)** - Project philosophy and design principles
- **[AVCPM.md](AVCPM.md)** - Quick reference card
- **[AVCPM_DESIGN.md](AVCPM_DESIGN.md)** - Detailed system design document
- **[PHASE2_PLAN.md](PHASE2_PLAN.md)** & **[PHASE3_PLAN.md](PHASE3_PLAN.md)** - Phase roadmaps

## Contributing

Contributions welcome! Please ensure:
1. Code follows the existing style
2. Tests pass (`pytest`)
3. New features include appropriate tests
4. Documentation is updated accordingly
5. Security considerations are reviewed

## License

This project is provided as-is for educational and development purposes.

---

*AVCPM v3.0.0 - AI-Native Version Control & Project Management*
