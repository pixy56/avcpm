# AVCPM Phase 2 Plan

## Phase 1 Recap (Complete)
- ✅ Task management (create, move, list)
- ✅ Commit system with SHA256 checksums
- ✅ Merge system with approval gates
- ✅ Checksum validation
- ✅ Status dashboard
- ✅ Full integration tests
- ✅ Testable modules with configurable base_dir

## Phase 2 Goals

Make AVCPM actually usable for real work by adding:
1. **Agent identity & signatures** - Know who did what
2. **Task dependencies** - Tasks that block other tasks
3. **Branching model** - Work on multiple things in parallel
4. **Conflict detection** - Detect when merges would conflict

---

## Phase 2 Tasks

### P0: Agent Identity System
**Problem:** Can't tell which agent made a commit
**Solution:** Add agent identity with signatures

| Task | Description | Est |
|------|-------------|-----|
| TASK-AGENT-01 | Create agent identity system (key pairs) | 2-3 hrs |
| TASK-AGENT-02 | Sign commits with agent keys | 2 hrs |
| TASK-AGENT-03 | Verify commit signatures on merge | 2 hrs |

**Deliverable:** `avcpm_agent.py` + signature verification

---

### P1: Task Dependencies
**Problem:** Tasks are flat, no blocking relationships
**Solution:** Add dependency tracking

| Task | Description | Est |
|------|-------------|-----|
| TASK-DEPS-01 | Add depends_on field to tasks | 1 hr |
| TASK-DEPS-02 | Block task progression if deps incomplete | 2 hrs |
| TASK-DEPS-03 | Visualize dependency graph in status | 2 hrs |

**Deliverable:** `avcpm_deps.py` + status updates

---

### P2: Branching Model
**Problem:** Only one staging area, can't work on multiple things
**Solution:** Branch-based staging

| Task | Description | Est |
|------|-------------|-----|
| TASK-BRANCH-01 | Create branch system (like git branches) | 3-4 hrs |
| TASK-BRANCH-02 | Branch creation, switching, listing | 2 hrs |
| TASK-BRANCH-03 | Merge branches with conflict detection | 3-4 hrs |

**Deliverable:** `avcpm_branch.py` + updated merge system

---

### P3: Conflict Detection
**Problem:** Merging blindly overwrites files
**Solution:** Detect when two branches touched same file

| Task | Description | Est |
|------|-------------|-----|
| TASK-CONFLICT-01 | Track file origins in ledger | 2 hrs |
| TASK-CONFLICT-02 | Detect conflicts during merge | 2 hrs |
| TASK-CONFLICT-03 | Present conflict resolution UI | 2 hrs |

**Deliverable:** `avcpm_conflict.py`

---

## Recommended Execution Order

```
Week 1:
├── Spawn: Agent Identity System
└── Spawn: Task Dependencies (can run parallel)

Week 2:
├── Spawn: Branching Model
└── Spawn: Conflict Detection (after branching)

Week 3:
└── Integration testing + Phase 2 sign-off
```

## Success Criteria

- [ ] Agents can sign their commits
- [ ] Tasks can depend on other tasks
- [ ] Multiple staging branches supported
- [ ] Conflicts detected before destructive merges
- [ ] All features tested
- [ ] Documentation updated

## First Task

**TASK-AGENT-01: Agent Identity System**

Create `avcpm_agent.py` that:
- Generates RSA key pairs per agent
- Stores keys in `.avcpm/agents/`
- Signs commits with private key
- Verifies signatures on merge

This unlocks everything else (trust, accountability, audit trail).

---

Ready to start?
