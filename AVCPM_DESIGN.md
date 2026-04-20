# System Design Document: AI-Native Version Control & Project Management (AVCPM)

## 1. Overview
The AVCPM is a lightweight, file-based system designed specifically for AI agents to collaborate on codebase evolution without the overhead of traditional Git if not desired, or as a layer on top of it to provide AI-specific metadata (intent, reasoning, and task linkage).

## 2. Core Objectives
- **Traceability:** Every change must be linked to a specific task/ticket.
- **Intent-Based Versioning:** Capturing *why* a change was made, not just *what* changed.
- **Agent Coordination:** Providing a central source of truth for task status and ownership.
- **Review Workflow:** A structured way for one agent to propose changes and another to audit/approve them.

## 3. Component Architecture

### 3.1. The Ledger (Commit Logs)
Instead of binary blobs, we will use a structured directory (`.avcpm/ledger/`) containing:
- **Commit Entries:** JSON or Markdown files containing:
    - `timestamp`, `agent_id`, `task_id`.
    - `changes`: List of files modified.
    - `rationale`: Detailed explanation of the logic.
    - `checksum`: To ensure integrity.

### 3.2. Branch Simulation (Workspaces)
To avoid polluting the main workspace:
- **Feature Folders:** Agents work in `workspaces/feature-<name>/`.
- **Staging:** A `staging/` area where changes are placed for review before being "merged" into the primary project directory.

### 3.3. Task Board (Project Management)
A directory-based Kanban system (`.avcpm/tasks/`):
- **Columns:** `todo/`, `in-progress/`, `review/`, `done/`.
- **Task Files:** Each task is a file containing:
    - `description`, `priority`, `assignee`.
    - `dependencies`: Other task IDs that must be finished first.
    - `status_history`: Log of transitions.

### 3.4. Code Review System
- **Review Requests:** Created in `.avcpm/reviews/`.
- **Feedback Loop:** Reviewers add `comments.md` to the review folder.
- **Approval Gate:** A final `APPROVED` flag required before a merge script moves files from staging to production.

## 4. Implementation Roadmap

### Phase 1: Infrastructure (The Core)
- Build the directory structure.
- Implement basic CLI tools/scripts for:
    - `avcpm task create` / `avcpm task move`
    - `avcpm commit` (writes to ledger and copies to staging)
    - `avcpm merge` (moves from staging to main)

### Phase 2: Automation & Validation
- Implement automated checksums.
- Build a "Status Report" generator that summarizes active tasks and recent commits.

### Phase 3: Testing & Migration
- Dry-run with a sample project.
- Migrate current dev team logs into the new ledger.
