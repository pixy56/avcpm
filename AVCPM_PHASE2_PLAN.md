# AVCPM Phase 2 Plan: Automation, Workflows & Intelligence

**Status:** Planning Complete  
**Scope:** Workflow automation, multi-agent coordination, enhanced validation, and intelligent features  
**Prerequisite:** Phase 1 Core (Complete ✓)

---

## Executive Summary

Phase 2 transforms AVCPM from a "file-based tracker" into an "AI-native coordination platform." The focus is on **automation** (reducing manual steps), **safety** (preventing errors before they happen), and **intelligence** (surfacing insights from the data).

### Key Theme: "From Manual to Automatic"

| Phase 1 (Manual) | Phase 2 (Automated) |
|------------------|---------------------|
| Move tasks by hand | Tasks auto-transition on commit/merge |
| Create review files manually | Review workflow with CLI commands |
| Single workspace | Multiple feature workspaces |
| No dependency checks | Blocked if dependencies incomplete |
| No conflict detection | Detect overlapping work |
| Basic reporting | Agent velocity & trend analysis |

---

## Phase 2 Scope

### P2.1: Workspace Management System
**Problem:** All work happens in a single directory. Agents can't work in parallel on different features without stepping on each other.

**Solution:** Feature workspace system with isolated working directories.

**Features:**
- `avcpm workspace create <name>` - Create isolated feature workspace
- `avcpm workspace list` - Show all active workspaces
- `avcpm workspace switch <name>` - Switch active context
- `avcpm workspace delete <name>` - Clean up merged/abandoned workspaces
- Automatic `.avcpm/workspaces/<name>/` directory structure
- Workspace-aware commit (commits go to workspace, not global staging)

**Success Criteria:**
- Multiple agents can work in parallel workspaces
- Workspace isolation prevents file conflicts
- Commits are workspace-scoped

---

### P2.2: Automated Task Lifecycle
**Problem:** Task status changes require manual `move` commands. Agents forget to update status.

**Solution:** Hook task transitions to actions automatically.

**Features:**
- Auto-move task to "in-progress" on first commit
- Auto-move task to "review" when commit is created
- Auto-move task to "done" on successful merge
- `avcpm task assign <id> <agent>` - Claim ownership
- `avcpm task deps <id> --add <dep_id>` / `--remove <dep_id>` - Manage dependencies
- Block task movement if dependencies not in "done"
- Dependency graph visualization (`avcpm task graph`)

**Success Criteria:**
- Tasks transition automatically based on actions
- Cannot move task if dependencies incomplete
- Clear visibility into blocked tasks

---

### P2.3: Structured Review Workflow
**Problem:** Reviews are just text files with "APPROVED" strings. No workflow, no comments, no assignments.

**Solution:** Full review lifecycle with CLI tooling.

**Features:**
- `avcpm review request <commit_id>` - Submit for review
- `avcpm review assign <commit_id> <reviewer>` - Assign reviewer
- `avcpm review comment <commit_id> "<message>"` - Add comment
- `avcpm review approve <commit_id>` - Approve with optional notes
- `avcpm review reject <commit_id> "<reason>"` - Request changes
- `avcpm review list` - Show pending reviews
- Review status: pending → in-review → approved/rejected
- Comments threaded with timestamps
- Reviewer workload balancing suggestions

**Success Criteria:**
- Complete review lifecycle managed via CLI
- Comments stored in structured format
- Cannot merge without approval
- Rejected commits must be re-committed after changes

---

### P2.4: File Diff & History
**Problem:** No visibility into what changed between versions. Can't compare commits.

**Solution:** Diff engine and file history tracking.

**Features:**
- `avcpm diff <commit_id>` - Show changes in a commit
- `avcpm diff <commit_a> <commit_b>` - Compare two commits
- `avcpm history <file>` - Show all versions of a file
- `avcpm show <commit_id>` - Display commit details
- Unified diff output (like `git diff`)
- Binary file detection (skip diff, show metadata)
- Side-by-side HTML diff generation (optional)

**Success Criteria:**
- Can view what changed in any commit
- Can compare arbitrary commits
- Can see full history of a file

---

### P2.5: Rollback & Recovery
**Problem:** No way to undo. Merged bad code? Manual cleanup required.

**Solution:** Safe rollback capabilities.

**Features:**
- `avcpm rollback <commit_id>` - Revert a merged commit
- `avcpm unstage <commit_id>` - Remove from staging
- `avcpm restore <file> [commit_id]` - Restore file to specific version
- Automatic backup before rollback
- Rollback validation (check for subsequent dependent commits)
- `avcpm reset --soft <commit_id>` - Keep changes, just move pointer
- `avcpm reset --hard <commit_id>` - Full reset to commit state

**Success Criteria:**
- Can revert any merged commit
- Backups created before destructive operations
- Warns if rollback would break dependencies

---

### P2.6: Multi-Agent Conflict Detection
**Problem:** Two agents can work on the same file simultaneously without knowing.

**Solution:** Work-in-progress tracking and conflict prediction.

**Features:**
- `avcpm wip claim <file>` - Mark file as being worked on
- `avcpm wip release <file>` - Mark file as available
- `avcpm wip list` - Show claimed files
- Pre-commit warning if file claimed by another agent
- Conflict prediction: warn if committing to file another agent has in-flight
- `avcpm status --conflicts` - Show potential conflicts
- Stale WIP detection (auto-release after timeout)

**Success Criteria:**
- Agents know what others are working on
- Warnings before conflicting commits
- No false positives (understand task boundaries)

---

### P2.7: Enhanced Validation & Safety
**Problem:** Validation only checks checksums. No semantic validation.

**Solution:** Multi-layer validation system.

**Features:**
- `avcpm validate --full` - Complete system check
- Circular dependency detection in tasks
- Orphaned commit detection (commits not linked to tasks)
- Zombie task detection (done but no commits)
- Unused staging file cleanup
- Ledger integrity check (corruption detection)
- Pre-commit hooks (configurable validation)
- Custom validation rules (JSON schema for task files)
- `avcpm doctor` - One-command health diagnostic

**Success Criteria:**
- `avcpm doctor` identifies all common issues
- Automatic cleanup of orphaned files
- Pre-commit validation catches errors

---

### P2.8: Intelligence & Analytics
**Problem:** Data exists but no insights. Can't track velocity or predict completion.

**Solution:** Analytics engine with trend reporting.

**Features:**
- `avcpm stats` - Summary statistics
- `avcpm stats --agent <name>` - Agent performance
- `avcpm stats --trends` - Velocity over time
- `avcpm report weekly` - Generate weekly summary
- Task completion time tracking (created → done)
- Agent workload dashboard
- Sprint/iteration tracking
- Burndown chart generation (ASCII or HTML)
- Prediction: "Based on velocity, 3 tasks remaining = ~2 days"

**Success Criteria:**
- Can generate weekly reports automatically
- Can estimate completion time
- Can identify bottlenecks

---

### P2.9: Unified CLI Interface
**Problem:** 5 separate scripts to run. No global config or help.

**Solution:** Single entry point with subcommands.

**Features:**
- `avcpm <command>` - Single entry point
- `avcpm --version` - Version info
- `avcpm --config <file>` - Config file support
- Shell completion generation
- Consistent flags across commands
- Colorized output (optional)
- Verbose/quiet modes

**Success Criteria:**
- One command to rule them all
- Consistent interface
- Configurable defaults

---

## Implementation Priority

### Wave 1: Foundation (Must Have)
**Order matters - these build on each other.**

1. **P2.9 Unified CLI** - Provides foundation for all other commands
2. **P2.4 File Diff & History** - Core capability for debugging
3. **P2.5 Rollback & Recovery** - Safety net for Wave 2
4. **P2.7 Enhanced Validation** - Stability before adding complexity

### Wave 2: Collaboration (Should Have)
**Enable multi-agent workflows.**

5. **P2.1 Workspace Management** - Parallel development
6. **P2.6 Multi-Agent Conflict Detection** - Coordination safety
7. **P2.3 Structured Review Workflow** - Quality gates

### Wave 3: Automation (Nice to Have)
**Reduce manual overhead.**

8. **P2.2 Automated Task Lifecycle** - Workflow automation
9. **P2.8 Intelligence & Analytics** - Insights and reporting

---

## Dependencies & Blockers

| Feature | Depends On | Blockers |
|---------|------------|----------|
| P2.1 Workspaces | P2.9 Unified CLI | None |
| P2.2 Auto Task Lifecycle | P2.3 Reviews, P2.1 Workspaces | None |
| P2.3 Reviews | P2.9 Unified CLI | None |
| P2.4 Diff/History | P2.9 Unified CLI | None |
| P2.5 Rollback | P2.4 History | None |
| P2.6 Conflict Detection | P2.1 Workspaces | None |
| P2.7 Enhanced Validation | P2.9 Unified CLI | None |
| P2.8 Analytics | P2.2 Auto Lifecycle | Need timestamps |
| P2.9 Unified CLI | Phase 1 Core | None |

**Critical Path:** P2.9 → P2.4 → P2.5 → P2.1 → P2.6

---

## Agent Role Assignments

| Component | Primary Role | Skills Needed |
|-----------|--------------|---------------|
| P2.9 Unified CLI | CLI Developer | Argparse, command dispatch |
| P2.4 Diff Engine | Core Developer | Diff algorithms, text processing |
| P2.5 Rollback | Core Developer | File operations, backup strategies |
| P2.1 Workspaces | Systems Developer | Directory management, context switching |
| P2.6 Conflict Detection | Systems Developer | State tracking, inter-process communication |
| P2.3 Reviews | Workflow Developer | State machines, approval flows |
| P2.2 Task Automation | Workflow Developer | Event hooks, dependency graphs |
| P2.7 Validation | QA/Developer | Testing, validation rules |
| P2.8 Analytics | Data Developer | Statistics, reporting, visualization |

---

## Success Criteria (Phase 2 Complete)

### Functional
- [ ] Single `avcpm` command runs all operations
- [ ] Can create and switch between workspaces
- [ ] Can view diff between any two commits
- [ ] Can rollback any commit safely
- [ ] Review workflow: request → assign → comment → approve/reject
- [ ] Tasks auto-transition on commit/merge
- [ ] Can claim files to prevent conflicts
- [ ] `avcpm doctor` passes all checks

### Quality
- [ ] All features have unit tests
- [ ] Integration tests cover multi-agent scenarios
- [ ] Documentation updated with new commands
- [ ] No breaking changes to Phase 1 data

### Performance
- [ ] Status check < 1 second for 100 tasks
- [ ] Diff generation < 500ms for 1000 line files
- [ ] Workspace switch < 200ms

---

## Recommended First Implementation

**Start with P2.9 (Unified CLI)** because:
1. Unblocks all other work (provides command structure)
2. No dependencies on other Phase 2 features
3. Immediately improves UX
4. Can be implemented incrementally (wrap existing scripts)

**Implementation approach:**
```python
# avcpm/__main__.py - Entry point
# avcpm/cli.py - Command dispatch
# avcpm/commands/task.py - Task subcommands
# avcpm/commands/commit.py - Commit subcommands
# etc.
```

---

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| Complexity explosion | Strict Wave 1 → 2 → 3 ordering |
| Data migration issues | Maintain Phase 1 compatibility layer |
| Performance degradation | Benchmark each feature |
| Multi-agent coordination bugs | Extensive integration testing |

---

## Next Steps

1. **Review and approve this plan**
2. **Create Phase 2 tracking task** in AVCPM
3. **Assign P2.9 (Unified CLI)** to first available agent
4. **Set up integration test harness** for multi-agent scenarios
5. **Begin Wave 1 implementation**

---

*Plan version: 1.0*  
*Created: 2026-04-19*  
*Target completion: TBD based on agent availability*
