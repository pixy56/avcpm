# AVCPM Phase 3 Plan: Production-Ready Multi-Agent Coordination

**Status:** Planning  
**Scope:** Branching model, conflict detection, production hardening  
**Prerequisite:** Phase 1 & 2 Complete ✓

---

## 1. Phase 3 Vision

### What "Complete" Looks Like

AVCPM Phase 3 transforms the system from a **capable prototype** into a **production-ready platform** for multi-agent software development. It solves the remaining coordination problems that prevent real-world usage at scale.

### Core Problems Phase 3 Solves

| Problem | Current State | Phase 3 Solution |
|---------|---------------|------------------|
| **No parallel development** | Single staging area, agents block each other | Full branching model with isolated workspaces |
| **Silent overwrites** | Merge blindly copies files | Conflict detection with 3-way merge capability |
| **No history navigation** | Can't see what changed between versions | Complete diff/blame/history system |
| **No recovery from mistakes** | One-way merges, no rollback | Full rollback, restore, and recovery tools |
| **Manual everything** | Agents must remember all steps | Automated workflows with lifecycle hooks |
| **Coordination blindness** | Don't know what others are doing | WIP tracking, conflict prediction, awareness |

### The Promise

By the end of Phase 3, multiple AI agents will be able to:

- **Work in parallel** on different features without interference
- **Detect conflicts** before they cause data loss
- **Review changes** with full diff visibility
- **Recover from errors** safely and predictably
- **Coordinate automatically** through the system, not through chat
- **Trust the system** to prevent common mistakes

---

## 2. Core Features (Must-Haves)

### 2.1 Branching Model (Phase 2 Deferred)

**Problem:** Single staging area means only one feature can be in-flight at a time. Agents must wait for each other.

**Solution:** Git-like branching with AVCPM-native simplicity.

**Features:**
- `avcpm branch create <name>` - Create isolated feature branch
- `avcpm branch list` - Show all branches with status
- `avcpm branch switch <name>` - Switch active branch context
- `avcpm branch delete <name>` - Clean up merged/abandoned branches
- `avcpm branch rename <old> <new>` - Rename branches
- Branch-aware commit (commits go to branch-specific staging)
- `.avcpm/branches/<branch>/` directory structure
- Main/production branch protection
- Branch metadata: created_by, created_at, parent_branch, task_id

**Data Structure:**
```json
{
    "branch_id": "feature-auth",
    "created_by": "agent-1234",
    "created_at": "2026-04-19T10:00:00Z",
    "parent_branch": "main",
    "parent_commit": "20260418120000",
    "task_id": "TASK-42",
    "status": "active"
}
```

---

### 2.2 Conflict Detection (Phase 2 Deferred)

**Problem:** Two agents modify the same file → last merge wins silently.

**Solution:** Multi-layer conflict detection with resolution workflow.

**Features:**
- **Pre-commit detection:** Warn if file modified in other branch
- **Merge-time detection:** Identify overlapping changes
- **Three-way merge:** Base + branch A + branch B = merged result
- **Conflict markers:** Standard `<<<<<<<` / `=======` / `>>>>>>>` format
- **Conflict resolution UI:** Interactive or auto-resolution strategies
- **Conflict tracking:** `.avcpm/conflicts/` directory
- **Auto-merge:** When changes don't overlap, merge automatically

**Conflict Types Detected:**
- **Content conflict:** Same lines modified in both branches
- **Delete/modify conflict:** One branch deletes, other modifies
- **Rename conflict:** Both branches rename same file differently
- **Directory conflict:** Structural changes conflict

**Resolution Strategies:**
- `ours` - Keep current branch version
- `theirs` - Keep incoming branch version
- `union` - Combine non-overlapping changes
- `manual` - Mark for hand resolution

---

### 2.3 Complete Diff & History System

**Problem:** Can't see what changed between versions. Debugging is guesswork.

**Solution:** Full version history with powerful comparison tools.

**Features:**
- `avcpm diff <commit_id>` - Show changes in a commit
- `avcpm diff <commit_a> <commit_b>` - Compare any two commits
- `avcpm diff <branch_a> <branch_b>` - Compare branch tips
- `avcpm history <file>` - Show all versions of a file
- `avcpm blame <file>` - Line-by-line authorship
- `avcpm show <commit_id>` - Full commit details
- Unified diff output (git-compatible format)
- Side-by-side HTML diff generation
- Binary file handling (metadata only)
- Word-level diff for documentation

**Data Structure:**
```json
{
    "commit_id": "20260419120000",
    "parent_commit": "20260418100000",
    "diff_summary": {
        "files_changed": 3,
        "insertions": 45,
        "deletions": 12
    },
    "file_diffs": [...]
}
```

---

### 2.4 Rollback & Recovery System

**Problem:** No way to undo. Bad merge = manual cleanup.

**Solution:** Comprehensive safety net with backups.

**Features:**
- `avcpm rollback <commit_id>` - Revert a merged commit
- `avcpm unstage <commit_id>` - Remove from staging
- `avcpm restore <file> [commit_id]` - Restore file to version
- `avcpm reset --soft <commit_id>` - Keep changes, reset pointer
- `avcpm reset --hard <commit_id>` - Full reset (with backup)
- Automatic backup before destructive operations
- `avcpm backup create` - Manual checkpoint creation
- `avcpm backup list` - Show available backups
- `avcpm backup restore <id>` - Restore from backup
- Dependency-aware rollback (warn if other commits depend on this)

**Backup Strategy:**
```
.avcpm/backups/
├── 20260419120000-rollback/
│   └── [snapshot of workspace]
└── 20260419150000-manual/
    └── [manual checkpoint]
```

---

### 2.5 Work-in-Progress (WIP) Tracking

**Problem:** Agents don't know what others are working on until commit time.

**Solution:** Proactive coordination through claim system.

**Features:**
- `avcpm wip claim <file>` - Mark file as being worked on
- `avcpm wip claim <pattern>` - Claim multiple files (glob patterns)
- `avcpm wip release <file>` - Release file
- `avcpm wip list` - Show all claimed files
- `avcpm wip list --mine` - Show my claims
- `avcpm wip list --agent <id>` - Show claims by agent
- Pre-commit conflict warning
- Stale claim detection (auto-release after 24h)
- Task-bound claims (auto-release on task completion)
- Claim visualization in status dashboard

**Data Structure:**
```json
{
    "file": "src/auth.py",
    "claimed_by": "agent-1234",
    "claimed_at": "2026-04-19T10:00:00Z",
    "task_id": "TASK-42",
    "expires_at": "2026-04-20T10:00:00Z"
}
```

---

### 2.6 Automated Task Lifecycle

**Problem:** Task status changes require manual commands. Agents forget.

**Solution:** Event-driven automatic transitions.

**Features:**
- Auto-move task to "in-progress" on first commit
- Auto-move task to "review" on commit creation
- Auto-move task to "done" on successful merge
- Block commit if task not assigned to agent
- Block commit if task dependencies incomplete
- Block merge if review not approved
- Task state validation at every operation

**Lifecycle Rules:**
```
todo → in-progress: On first commit
todo → review: Blocked (must go through in-progress)
in-progress → review: On commit creation
in-progress → done: Blocked (must be reviewed)
review → done: On merge approval
review → in-progress: On rejection
```

---

## 3. Enhancement Features (Nice-to-Haves)

### 3.1 Production Hardening

**Goal:** Make AVCPM enterprise-ready.

| Feature | Description |
|---------|-------------|
| **Integrity Checks** | Cryptographic verification of all ledger entries |
| **Audit Logging** | Immutable log of all system actions |
| **Access Control** | Role-based permissions (read/write/admin) |
| **Encryption at Rest** | Encrypt sensitive files in staging |
| **Compression** | Compress archived branches and old commits |
| **Garbage Collection** | Clean up orphaned files and old backups |

---

### 3.2 Performance & Scale

**Goal:** Support 100+ agents, 1000+ tasks.

| Feature | Description |
|---------|-------------|
| **Lazy Loading** | Load task data on-demand, not all at startup |
| **Caching Layer** | Cache checksums, metadata, status |
| **Parallel Operations** | Concurrent validation, bulk operations |
| **Snapshotting** | Fast branch creation via copy-on-write |
| **Index Files** | Quick lookup for commits, tasks, agents |
| **Streaming Diff** | Handle large files without loading into memory |

**Performance Targets:**
- Task list: < 500ms for 1000 tasks
- Diff generation: < 1s for 10k line files
- Branch switch: < 300ms
- Status check: < 1s for full system

---

### 3.3 Developer Experience

**Goal:** Make AVCPM delightful to use.

| Feature | Description |
|---------|-------------|
| **Unified CLI** | Single `avcpm` entry point with subcommands |
| **Shell Completion** | Tab completion for bash/zsh/fish |
| **Colorized Output** | Syntax highlighting for diffs, status |
| **Progress Indicators** | Show progress for long operations |
| **Interactive Mode** | `avcpm interactive` - TUI dashboard |
| **Config File** | `.avcpmrc` for default settings |
| **Hooks System** | Pre/post commit, merge, validation hooks |
| **Plugin Architecture** | Extensible command system |

---

### 3.4 Integration & Interop

**Goal:** Play nicely with existing tools.

| Feature | Description |
|---------|-------------|
| **Git Bridge** | Bidirectional sync with Git repositories |
| **GitHub/GitLab Integration** | PR/Issue sync |
| **Web Dashboard** | Browser-based status view |
| **API Server** | HTTP API for external tools |
| **Webhook Support** | Notify external systems on events |
| **Export/Import** | JSON/CSV export for analysis |

---

### 3.5 Intelligence & Analytics

**Goal:** Learn from data to improve workflows.

| Feature | Description |
|---------|-------------|
| **Agent Velocity Tracking** | Commits/tasks per day by agent |
| **Conflict Prediction** | ML-based conflict likelihood |
| **Bottleneck Detection** | Identify blocked tasks, slow reviews |
| **Code Churn Analysis** | Files that change frequently |
| **Sprint Reporting** | Burndown charts, completion forecasts |
| **Review Load Balancing** | Suggest reviewers based on workload |
| **Automatic Tagging** | Suggest task categories from content |

---

## 4. Technical Architecture

### 4.1 New Modules Required

| Module | Purpose | Key Functions |
|--------|---------|---------------|
| `avcpm_branch.py` | Branch lifecycle management | create, switch, delete, list, get_current |
| `avcpm_conflict.py` | Conflict detection & resolution | detect, merge_three_way, resolve, mark_resolved |
| `avcpm_diff.py` | Diff generation & comparison | diff_commits, diff_files, generate_patch, blame |
| `avcpm_rollback.py` | Recovery operations | rollback, unstage, restore, backup, reset |
| `avcpm_wip.py` | Work-in-progress tracking | claim, release, list, check_conflicts, expire_stale |
| `avcpm_lifecycle.py` | Automated task transitions | on_commit, on_merge, validate_transition |
| `avcpm_cli.py` | Unified CLI entry point | command dispatch, subcommand routing |

### 4.2 Changes to Existing Modules

| Module | Changes |
|--------|---------|
| `avcpm_commit.py` | Branch-aware staging, task validation, lifecycle hooks |
| `avcpm_merge.py` | Branch merge support, conflict handling, 3-way merge |
| `avcpm_task.py` | Lifecycle integration, dependency auto-checks |
| `avcpm_status.py` | Branch status, WIP display, conflict warnings |
| `avcpm_validate.py` | Branch consistency checks, cross-branch validation |
| `avcpm_agent.py` | Permission checks for branch operations |

### 4.3 Data Structure Updates

#### Branch Storage
```
.avcpm/
├── branches/
│   ├── main/
│   │   ├── branch.json       # Branch metadata
│   │   ├── staging/          # Branch-specific staging
│   │   └── commits/          # Branch-specific commit refs
│   └── feature-xyz/
│       ├── branch.json
│       └── staging/
└── current_branch            # Symlink or file with active branch
```

#### Enhanced Commit Ledger
```json
{
    "commit_id": "20260419120000",
    "branch": "feature-auth",
    "parent_commit": "20260418100000",
    "timestamp": "2026-04-19T12:00:00Z",
    "agent_id": "agent-1234",
    "task_id": "TASK-42",
    "rationale": "Add OAuth2 support",
    "changes": [...],
    "signature": "...",
    "merge_info": {
        "is_merge": false,
        "source_branch": null,
        "conflicts_resolved": 0
    }
}
```

#### Conflict Records
```json
{
    "conflict_id": "conf-20260419130000",
    "branch_a": "feature-auth",
    "branch_b": "main",
    "base_commit": "20260418100000",
    "status": "unresolved",
    "files": [
        {
            "path": "src/auth.py",
            "type": "content",
            "ours_checksum": "abc...",
            "theirs_checksum": "def...",
            "base_checksum": "ghi..."
        }
    ]
}
```

#### WIP Registry
```json
{
    "claims": {
        "src/auth.py": {
            "agent_id": "agent-1234",
            "task_id": "TASK-42",
            "claimed_at": "2026-04-19T10:00:00Z",
            "expires_at": "2026-04-20T10:00:00Z"
        }
    }
}
```

### 4.4 Index Files (Performance)

```
.avcpm/index/
├── task_index.json      # Task ID → file path lookup
├── commit_index.json    # Commit ID → branch, timestamp lookup
├── file_index.json      # File path → commits that touched it
└── agent_index.json     # Agent ID → commits, tasks
```

---

## 5. Implementation Plan

### 5.1 Wave 1: Foundation (Weeks 1-2)
**Foundation for everything else. Must be solid.**

| Task | Module | Est | Depends |
|------|--------|-----|---------|
| TASK-BR-01 | Branch data structures | 4h | None |
| TASK-BR-02 | Branch create/list/delete | 4h | TASK-BR-01 |
| TASK-BR-03 | Branch switch context | 4h | TASK-BR-02 |
| TASK-BR-04 | Branch-aware commit | 4h | TASK-BR-03 |
| TASK-DF-01 | Diff algorithm (unified) | 6h | None |
| TASK-DF-02 | Diff commits/files | 4h | TASK-DF-01 |
| TASK-DF-03 | File history tracking | 4h | TASK-DF-02 |

**Wave 1 Deliverable:** Branch system + diff working, all tested

---

### 5.2 Wave 2: Safety (Weeks 3-4)
**Prevent disasters, enable recovery.**

| Task | Module | Est | Depends |
|------|--------|-----|---------|
| TASK-CF-01 | 3-way diff algorithm | 6h | TASK-DF-01 |
| TASK-CF-02 | Conflict detection | 4h | TASK-CF-01, TASK-BR-04 |
| TASK-CF-03 | Conflict markers | 4h | TASK-CF-02 |
| TASK-CF-04 | Conflict resolution UI | 6h | TASK-CF-03 |
| TASK-RB-01 | Backup system | 4h | None |
| TASK-RB-02 | Rollback implementation | 4h | TASK-RB-01 |
| TASK-RB-03 | Restore commands | 4h | TASK-RB-02 |
| TASK-RB-04 | Reset commands | 4h | TASK-RB-02 |

**Wave 2 Deliverable:** Conflict detection + rollback working

---

### 5.3 Wave 3: Coordination (Weeks 5-6)
**Enable multi-agent awareness.**

| Task | Module | Est | Depends |
|------|--------|-----|---------|
| TASK-WP-01 | WIP claim/release | 4h | None |
| TASK-WP-02 | WIP conflict detection | 4h | TASK-WP-01 |
| TASK-WP-03 | Stale claim cleanup | 2h | TASK-WP-01 |
| TASK-WP-04 | WIP in status | 2h | TASK-WP-01 |
| TASK-LC-01 | Lifecycle event system | 4h | None |
| TASK-LC-02 | Auto task transitions | 4h | TASK-LC-01 |
| TASK-LC-03 | Lifecycle validation | 4h | TASK-LC-02 |
| TASK-LC-04 | Integration with commit/merge | 4h | TASK-LC-03, TASK-BR-04 |

**Wave 3 Deliverable:** WIP tracking + auto-lifecycle working

---

### 5.4 Wave 4: Polish (Week 7)
**Make it production-ready.**

| Task | Module | Est | Depends |
|------|--------|-----|---------|
| TASK-CLI-01 | Unified CLI structure | 6h | All above |
| TASK-CLI-02 | Shell completion | 2h | TASK-CLI-01 |
| TASK-VAL-01 | Enhanced validation | 4h | All above |
| TEST-INT-01 | Integration tests | 8h | All above |
| TEST-E2E-01 | End-to-end scenarios | 8h | TEST-INT-01 |
| DOC-01 | Documentation update | 6h | All above |

**Wave 4 Deliverable:** Phase 3 complete, fully tested

---

### 5.5 Execution Order & Dependencies

```
Week 1: Branch Foundation
├── TASK-BR-01 (data structures)
├── TASK-BR-02 (create/list)
├── TASK-BR-03 (switch)
└── TASK-BR-04 (branch-aware commit)

Week 2: Diff System
├── TASK-DF-01 (diff algorithm)
├── TASK-DF-02 (diff commits)
└── TASK-DF-03 (file history)

Week 3: Conflict Detection
├── TASK-CF-01 (3-way diff) [needs TASK-DF-01]
├── TASK-CF-02 (detection) [needs TASK-BR-04]
└── TASK-CF-03 (markers)

Week 4: Recovery
├── TASK-RB-01 (backup)
├── TASK-RB-02 (rollback)
├── TASK-RB-03 (restore)
└── TASK-CF-04 (resolution UI) [needs TASK-CF-03]

Week 5: WIP Tracking
├── TASK-WP-01 (claim/release)
├── TASK-WP-02 (conflict detection)
├── TASK-WP-03 (stale cleanup)
└── TASK-WP-04 (status integration)

Week 6: Lifecycle
├── TASK-LC-01 (event system)
├── TASK-LC-02 (auto transitions)
├── TASK-LC-03 (validation)
└── TASK-LC-04 (integration) [needs TASK-BR-04]

Week 7: Polish & Test
├── TASK-CLI-01 (unified CLI)
├── TASK-CLI-02 (completion)
├── TEST-INT-01 (integration)
├── TEST-E2E-01 (e2e)
└── DOC-01 (docs)
```

---

### 5.6 Roles Needed

| Role | Responsibilities | Tasks |
|------|------------------|-------|
| **Core Developer** | Branch/diff/conflict algorithms | TASK-BR-*, TASK-DF-*, TASK-CF-* |
| **Systems Developer** | Recovery, backup, safety | TASK-RB-* |
| **Workflow Developer** | Lifecycle, WIP, automation | TASK-LC-*, TASK-WP-* |
| **CLI Developer** | Unified interface, UX | TASK-CLI-* |
| **QA Engineer** | Testing, validation | TEST-*, TASK-VAL-* |
| **Technical Writer** | Documentation | DOC-* |

---

## 6. Success Criteria

### 6.1 Functional Requirements

| Criteria | How Verified |
|----------|--------------|
| Can create/switch/delete branches | Integration test |
| Can commit to specific branch | Integration test |
| Can merge branches with auto-merge | Integration test |
| Conflicts detected when files overlap | Integration test |
| 3-way merge produces correct output | Unit test |
| Can view diff between any commits | Integration test |
| Can rollback any merged commit | Integration test |
| Can restore file to previous version | Integration test |
| WIP claims prevent conflicting commits | Integration test |
| Tasks auto-transition on events | Integration test |
| All operations have unified CLI | Manual test |

### 6.2 Quality Requirements

| Criteria | Target |
|----------|--------|
| Unit test coverage | > 90% |
| Integration test scenarios | > 20 |
| Code complexity (cyclomatic) | < 10 per function |
| Documentation completeness | 100% of public APIs |
| Error handling | All errors have user-friendly messages |

### 6.3 Performance Requirements

| Operation | Target |
|-----------|--------|
| Branch switch | < 300ms |
| Diff generation (1k lines) | < 500ms |
| Conflict detection (10 files) | < 200ms |
| Status check (100 tasks) | < 1s |
| Commit (10 files) | < 500ms |
| Merge (no conflicts) | < 1s |

### 6.4 Multi-Agent Requirements

| Scenario | Expected Behavior |
|----------|-------------------|
| Agent A on branch1, Agent B on branch2 | Both commit simultaneously without conflict |
| Agents modify same file on different branches | Conflict detected at merge time |
| Agent claims file, another tries to commit | Warning shown, can override |
| Agent A merges while Agent B committing | Merge blocked or B's commit goes to new commit |

---

## 7. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| 3-way merge algorithm bugs | Medium | High | Extensive testing, fallback to manual merge |
| Performance degradation with scale | Medium | Medium | Index files, lazy loading, caching |
| Data corruption during branch ops | Low | Critical | Backup before all destructive ops, validate integrity |
| Complexity explosion | Medium | Medium | Strict wave ordering, simplify features if needed |
| Breaking changes to Phase 1/2 data | Medium | High | Migration scripts, backward compatibility layer |

---

## 8. Definition of Done

Phase 3 is **complete** when:

### Must-Have (Blocking)
- [ ] All Wave 1-4 tasks complete
- [ ] All functional requirements met
- [ ] Unit test coverage > 90%
- [ ] Integration tests pass
- [ ] Documentation updated
- [ ] No critical bugs open

### Should-Have (Non-Blocking)
- [ ] Performance targets met
- [ ] Multi-agent scenarios tested
- [ ] Error handling comprehensive
- [ ] CLI unified and polished

### Nice-to-Have (Stretch)
- [ ] Shell completion working
- [ ] Example multi-agent workflow documented
- [ ] Stress tested with 100+ tasks

---

## 9. Next Steps

1. **Review and approve this plan**
2. **Create Phase 3 tracking task** in AVCPM
3. **Assign Wave 1 tasks** to available agents
4. **Set up branch** for Phase 3 development
5. **Begin implementation** with TASK-BR-01

---

## Appendix: Comparison with Git

| Feature | Git | AVCPM Phase 3 | Difference |
|---------|-----|---------------|------------|
| Branching | Full | Full | AVCPM branches linked to tasks |
| Conflicts | 3-way merge | 3-way merge | AVCPM has WIP pre-detection |
| Diff | Unified | Unified | Same format |
| Recovery | Reflog, reset | Backup, rollback | AVCPM more explicit |
| Identity | Config-based | RSA-signed | AVCPM cryptographically verifiable |
| Task tracking | None | Built-in | AVCPM native |
| Reviews | PRs | Built-in approval | AVCPM lightweight |

---

*Plan version: 1.0*  
*Created: 2026-04-19*  
*Target completion: 7 weeks from start*  
*Prerequisites: Phase 1 & 2 complete*
