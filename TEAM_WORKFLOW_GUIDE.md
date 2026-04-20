# Team Workflow Guide: AVCPM (Atomic Version Control & Process Management)

## Overview
This guide mandates the use of the AVCPM system for all development tasks. The goal is to ensure atomicity, traceability, and rigorous validation of every change introduced to the codebase.

## The Workflow

### 1. Task Initialization
Every piece of work must begin with a task file in `.avcpm/tasks/todo/`. 
- **Format**: `TASK-XXX.json`
- **Content**: Clear objectives, acceptance criteria, and assigned developer.

### 2. Development & Staging
Work must be performed in the `.avcpm/staging/` area or a designated feature branch. 
- No direct commits to main without an AVCPM review.
- Use checksums to verify the integrity of delivered artifacts.

### 3. Review & Validation
Once a task is complete, it moves to `.avcpm/tasks/review/`.
- A peer review must be conducted.
- The reviewer validates that the implementation meets the acceptance criteria and follows the system standards.

### 4. Finalization & Ledgering
Upon approval:
- The task is moved to `.avcpm/tasks/done/`.
- A final entry is recorded in the `.avcpm/ledger/` to provide an immutable history of the change.

## Mandate
Effective immediately, any work submitted without a corresponding AVCPM task and ledger entry will be considered "unauthorized" and will be sent back for reprocessing.
