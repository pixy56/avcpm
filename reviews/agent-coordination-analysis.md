# Agent Coordination Analysis: Self-Improving Skill Integration

**Date:** 2026-05-09
**Analyst:** Subagent (Agent Coordination Analyst)
**Sources:**
- `/raw/self-improving-agent-skill.md` — Skill description
- `/AGENTS.md` — Workspace conventions
- `/reviews/AVCPM-CODE-REVIEW-2026-05-09.md` — Multi-agent review example

---

## Current State Assessment

Our multi-agent review pipeline (exemplified by the AVCPM review) has **4 specialized agents** (Architecture, Security, Performance, Testing) with these operational parameters:
- Subagent timeout: **2 minutes / 16 tool calls**
- Agent lifecycle: spawn → run → kill via `sessions_yield`
- **Zero persistent learnings** transfer between reviews
- **Zero feedback loop** from results to future agent behavior
- Orchestrator decisions are **heuristic/static** (always same 4 agents, same limits)

The self-improving skill provides a structured `.learnings/` mechanism (LEARNINGS.md, ERRORS.md, FEATURE_REQUESTS.md) with ID-based tracking, priority/status fields, and promotion to AGENTS.md/SOUL.md/TOOLS.md/MEMORY.md.

---

## 1. Review Quality Over Time (Learning from Past Reviews)

### Current Gap
The AVCPM review found **19 distinct issues** across 4 categories. In the next review (different repo), agents start from zero. They will:
- Re-discover the same anti-patterns (e.g., `sys.exit()` in library functions)
- Miss the same subtle bug classes (e.g., TOCTOU races, symlink traversal)
- Re-write the same recommendation boilerplate

### How Self-Improving Skill Helps

| Mechanism | Implementation | Impact |
|-----------|---------------|--------|
| **Pattern Logging** | After each review, log `[LRN-YYYYMMDD-XXX]` entries for bug categories found | Agents reference prior patterns in pre-prompt context |
| **Agent-Specific Calibration** | Track which agent type (Security vs Testing) catches which bug class | Tune agent prompts to focus on their proven strengths |
| **Missed-Findings Tracking** | Log `[ERR-YYYYMMDD-XXX]` when post-review human audit finds missed issues | Promote to MEMORY.md as "known blind spots" |
| **Review Template Evolution** | Promote recurring recommendation structures to AGENTS.md | Reduce token waste on re-explaining standard fixes |

### Specific Recommendation: Review Quality Log
Create `.learnings/review-patterns.md` with entries like:
```markdown
- **ID:** [LRN-20260509-001]
- **Pattern:** `sys.exit()` inside library API functions
- **First Seen:** AVCPM review (Architecture agent)
- **Frequency:** 3/4 reviews (2026-04, 2026-05)
- **Detection Rate:** Architecture agent 100%, Security agent 0%
- **Action:** Add to Architecture agent pre-prompt as P0 check
- **Status:** promoted → AGENTS.md (agent pre-prompts section)
```

**Priority: P0** — Immediate quality multiplier with near-zero cost.

---

## 2. Subagent Optimization (Timeout Tuning, Model Selection)

### Current Gap
- **Static 2-minute / 16-tool limit** for all 4 agents regardless of task
- AVCPM Security review is **dense** (3 Critical, 5 High, 6 Medium, 5 Low) — likely hit tool limits
- AVCPM Testing review needed to inspect **12 test files + integration suite** — 16 calls is tight
- No data on which agents succeed/fail within their budgets

### How Self-Improving Skill Helps

| Metric to Log | Purpose | Promotion Target |
|---------------|---------|-----------------|
| Tool calls consumed per agent type | Right-size limits | AGENTS.md (spawn configs) |
| Timeout violations per agent | Identify under-budgeted agents | `.learnings/ERRORS.md` |
| Model used vs. success rate | Match model capability to task | TOOLS.md (model selection guide) |
| Files reviewed vs. findings density | Estimate appropriate tool budget | AGENTS.md |

### Specific Recommendation: Dynamic Limits File
Create `.learnings/subagent-metrics.md` with structured entries:
```markdown
- **ID:** [MET-20260509-001]
- **Agent:** Security
- **Repo Size:** 15 modules, ~4K LOC
- **Tool Calls Used:** 16/16 (hit limit)
- **Findings:** 14 issues logged, 3 truncated
- **Model:** ollama/kimi-k2.6:cloud
- **Suggested Action:** Increase Security agent to 24 tools or spawn 2-pass (critical-only then deep-dive)
- **Status:** pending
```

**Priority: P1** — Requires 3-5 review cycles to accumulate enough data, then high impact.

### Model Selection Intelligence
Current setup uses one model for all agents. Self-improving logs can track:
- Security agent on lightweight model → misses crypto nuance
- Architecture agent on reasoning model → over-analyzes trivial coupling
- Promote to `TOOLS.md` as "Model Selection Matrix"

---

## 3. Cross-Session Knowledge Sharing (What One Agent Learns, Others Know)

### Current Gap
- Architecture agent learns AVCPM has `sys.exit()` anti-pattern → dies with session
- Next review's Security agent doesn't know to check for `sys.exit()` as info-disclosure vector
- Testing agent doesn't know to look for `test_` prefix issues
- **Each agent is an island**

### How Self-Improving Skill Helps

The skill's **promotion mechanism** is the bridge:

```
Agent A finds pattern X in Review 1
  → Logged to .learnings/LEARNINGS.md
  → Heartbeat cron reviews logs weekly
  → Promoted to AGENTS.md / MEMORY.md
  → All future agents inherit via startup context
```

AGENTS.md already states: *"Use runtime-provided startup context first"* — this is the delivery channel.

### Specific Recommendation: Shared Agent Context Sections
Add to AGENTS.md (or new `.learnings/promoted.md` symlinked into startup context):

```markdown
## Multi-Agent Learnings (Auto-Promoted)

### Security Agent — Known Vulnerability Patterns
- Path traversal via unsanitized task IDs (C1-class)
- Symlink-following in backup/restore (H3-class)
- TOCTOU races in safe_copy (M4-class)
- Plaintext approval strings (H1-class)

### Architecture Agent — Structural Anti-Patterns
- Library functions calling sys.exit()
- CLI/library conflation
- Timestamp-based non-unique IDs
- Tight coupling without hook registry

### Performance Agent — Bottleneck Signatures
- No file locking + multi-agent usage
- Monolithic JSON registries
- Absence of LRU cache on disk reads
- O(n²) graph traversals

### Testing Agent — Coverage Blind Spots
- Untested auth/session modules
- Untested security/sanitization modules
- Untested ledger integrity chain
- Mixed test frameworks in same repo
```

**Priority: P0** — The infrastructure already exists (AGENTS.md + promotion). Just need discipline to log and promote.

---

## 4. Orchestrator Decision-Making (When to Spawn, Which Models, What Tasks)

### Current Gap
Orchestrator uses **fixed policy**: always spawn 4 agents, always same models, always same limits, always all files. No adaptivity for:
- Small repos (waste) vs. large repos (incomplete)
- Security-critical repos (need deeper Security pass) vs. internal tools
- Known-clean modules (skip?) vs. historically buggy modules (focus?)

### How Self-Improving Skill Helps

| Decision | Input from Learnings | Action |
|----------|---------------------|--------|
| **Which agents to spawn?** | `.learnings/agent-effectiveness.md` tracks hit rate per agent per repo type | Skip Testing agent if repo has 0 test files; add Compliance agent if repo handles PII |
| **Which model per agent?** | Logged success rate by model | Route Security to reasoning model, Testing to fast model |
| **What files to assign?** | `.learnings/file-risk-heatmap.md` from past reviews | Assign historically buggy modules to strongest agent |
| **Timeout budget allocation** | Average tool use per agent per LOC | Give Performance agent 3 min for large repos |
| **When to skip review?** | If `.avcpm/reviews/latest.md` exists and code unchanged | Skip, or run delta-only review |

### Specific Recommendation: Orchestrator Decision Matrix
Create `.learnings/orchestrator-rules.md`:
```markdown
## Spawn Rules (Auto-Promoted from Review History)

### Rule: Skip Testing Agent
**Condition:** `find . -name "test_*.py" | wc -l` == 0
**Action:** Do not spawn Testing agent; redirect budget to Security
**Source:** [LRN-20260509-004] — 3 reviews with 0 tests, Testing agent found nothing

### Rule: Security Deep-Dive
**Condition:** Repo has `auth.py`, `security.py`, `encrypt.py`, or handles file paths
**Action:** Spawn Security agent with 24 tools + reasoning model
**Source:** [LRN-20260509-005] — 100% of repos with auth modules had critical path traversal

### Rule: Architecture First
**Condition:** New repo (no prior `.learnings/` entries)
**Action:** Spawn Architecture agent first with broad scope; use its output to scope other agents
**Source:** [LRN-20260509-006] — Early architecture context improves other agents' focus by ~30%
```

**Priority: P1** — Needs 3-5 cycles of data before rules are actionable. High leverage once mature.

---

## Unified Priority Matrix

### 🔴 P0 — Implement Immediately

| # | Recommendation | Effort | Impact | Owner |
|---|---------------|--------|--------|-------|
| 1 | Create `.learnings/` directory with `LEARNINGS.md`, `ERRORS.md`, `review-patterns.md` | Low | High | Orchestrator |
| 2 | Add "Multi-Agent Learnings" section to AGENTS.md (or promoted.md) for shared startup context | Low | High | Analyst |
| 3 | After every review, log 3-5 top patterns with IDs, agent attribution, and promotion status | Low | High | Orchestrator |
| 4 | Hook into existing heartbeat/cron for weekly log review and promotion to AGENTS.md/MEMORY.md | Low | Medium | Heartbeat job |

### 🟠 P1 — Implement After 3-5 Review Cycles

| # | Recommendation | Effort | Impact | Owner |
|---|---------------|--------|--------|-------|
| 5 | Create `.learnings/subagent-metrics.md` to track tool usage, timeouts, model success per agent | Medium | High | Orchestrator |
| 6 | Create `.learnings/orchestrator-rules.md` with data-driven spawn/model/scope rules | Medium | High | Orchestrator |
| 7 | Tune subagent timeouts (2 min default → dynamic based on repo size + historical data) | Medium | Medium | Orchestrator |
| 8 | Add model-selection matrix to TOOLS.md based on agent type success rates | Low | Medium | Analyst |

### 🟡 P2 — Long-Term Enhancement

| # | Recommendation | Effort | Impact | Owner |
|---|---------------|--------|--------|-------|
| 9 | Build agent-specific pre-prompt templates that inject relevant `.learnings/` entries | Medium | Medium | Skill maintainer |
| 10 | Create "delta review" mode: skip unchanged modules by comparing to last review hash | Medium | Medium | Orchestrator |
| 11 | Automated promotion: heartbeat job promotes `[status: resolved]` learnings if seen >3 times | Low | Low | Cron job |
| 12 | Cross-repo pattern matching: "Repo X has same auth module as Repo Y → apply Security learnings" | High | High | Future work |

---

## Integration with Existing AGENTS.md Conventions

The self-improving skill **aligns perfectly** with existing workspace conventions:

| Existing Convention | Integration Point |
|--------------------|--------------------|
| "Write it down — no mental notes" | `.learnings/` is the canonical write-it-down location for agent behavior |
| Heartbeat for periodic maintenance | Heartbeat reviews `.learnings/` weekly and promotes to MEMORY.md |
| MEMORY.md for curated wisdom | Promoted learnings become MEMORY.md entries |
| AGENTS.md for workflow rules | Promoted learnings become AGENTS.md "Multi-Agent Learnings" section |
| TOOLS.md for environment specifics | Model-selection matrix goes here |
| Daily notes in `memory/YYYY-MM-DD.md` | Raw review logs go here; `.learnings/` is the distilled version |

---

## Suggested First Actions (This Week)

1. **Create directory:** `mkdir -p .learnings/`
2. **Seed LEARNINGS.md** with AVCPM review's top 5 patterns (path traversal, sys.exit, race conditions, etc.)
3. **Update AGENTS.md** with a "Multi-Agent Learnings" section referencing `.learnings/`
4. **Log first ERRORS.md entry:** Document that the current 16-tool limit truncated AVCPM Security findings
5. **Set heartbeat reminder:** Add `.learnings review` to `HEARTBEAT.md` checklist

---

*Analysis complete. Ready for integration into main agent workflow.*
