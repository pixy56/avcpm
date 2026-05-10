# Self-Improving Agent Integration Report

**Date:** 2026-05-09
**Skill:** https://clawhub.ai/pskoett/self-improving-agent
**Analysts:** 4 specialized agents (Memory, Automation, Agent Coordination, Error Management)

---

## Executive Summary

The self-improving-agent skill adds a **structured learning layer** (`.learnings/`) that sits between raw experience and curated memory. It turns ad-hoc notes into a compounding improvement engine.

**Biggest finding:** Our "4 cron jobs" are documented but **not actually installed**. They don't run automatically.

---

## Current System vs. Proposed

| Aspect | Current | With Self-Improving Skill |
|--------|---------|---------------------------|
| **Errors** | Scattered in MEMORY.md bullets | Structured `[ERR-YYYYMMDD-XXX]` entries with recovery steps |
| **Learnings** | Occasionally remembered | Logged immediately with priority, status, area |
| **Memory** | Manually curated | Auto-promoted from `.learnings/` via weekly review |
| **Cron jobs** | Documented but **not scheduled** | Verified, logged, tracked in `.learnings/CRON_LOG.md` |
| **Performance** | Anecdotal ("Ollama is slow") | Measured baselines in `.learnings/PERFORMANCE.md` |
| **Agent reviews** | Stateless (start from zero each time) | Pattern inheritance via promoted AGENTS.md entries |

---

## Key Findings by Area

### 🔴 Critical: Automation Layer

**Discovery:** The 4 cron jobs (graphify daily, wiki ingest 6h, log review 6h, weekly lint) are **listed in HEARTBEAT.md but not installed in any crontab**. They run only when manually triggered.

**Fix:**
1. Actually install the cron jobs (or use OpenClaw's native scheduler)
2. Add cron verification to heartbeat
3. Log every run to `.learnings/CRON_LOG.md`

### 🟡 High: Error Management

**Today's 9 issues** (from this session) would be structured as:
- `[ERR-20260509-001]` Subagent timeout at 16 tools
- `[ERR-20260509-002]` `gh repo sync --force` wiped local work
- `[ERR-20260509-003]` Graphify needed `openai` package
- `[ERR-20260509-004]` Search index UNIQUE constraint failed
- `[ERR-20260509-005]` Ollama semantic extraction slow
- `[ERR-20260509-006]` gog keyring timeout
- `[ERR-20260509-007]` gog Drive API not enabled
- `[ERR-20260509-008]` Browser auth flow requires manual intervention
- `[ERR-20260509-009]` Chromium permission denied for PDF

**Fix:** Create `.learnings/ERRORS.md` with these entries + recovery steps.

### 🟡 High: Agent Coordination

**Current:** 4 review agents spawn with fixed 2-minute/16-tool limits, then die with their insights.

**Fix:**
- Log review patterns after each review (e.g., "path traversal found in 3/4 reviews")
- Promote to AGENTS.md "Multi-Agent Learnings" section
- Future agents inherit known anti-patterns at startup

### 🟡 High: Memory Systems

**Current:** MEMORY.md is manually updated, only 3 lessons. Daily logs are 20 days stale.

**Fix:**
- `.learnings/LEARNINGS.md` captures insights immediately
- Weekly cron promotes high-priority items to MEMORY.md
- Deprecate heavy daily log reliance (keep for raw session logs only)

---

## Proposed `.learnings/` Structure

```
workspace/.learnings/
├── LEARNINGS.md          # Corrections, insights, best practices
├── ERRORS.md             # Command failures, exceptions
├── FEATURE_REQUESTS.md   # User requests + automation gaps
├── CRON_LOG.md           # Structured cron execution log
├── HEARTBEAT_EVAL.md     # Check usefulness tracking
├── PERFORMANCE.md        # Timing baselines and trends
├── review-patterns.md    # Multi-agent review anti-patterns
└── subagent-metrics.md   # Tool usage, timeouts, model success
```

---

## Integration with Existing Files

| Learning Type | Promote To | Example |
|---------------|-----------|---------|
| Behavioral patterns | SOUL.md | "Be concise, avoid disclaimers" |
| Workflow improvements | AGENTS.md | "Spawn sub-agents for long tasks" |
| Tool gotchas | TOOLS.md | "Git push needs auth configured first" |
| Knowledge gaps | MEMORY.md | "Graphify requires openai package for Ollama" |
| Performance issues | HEARTBEAT.md | "Ollama >5min → fallback to AST-only" |

---

## Top 5 Action Items (Prioritized)

| Priority | Action | Effort | Impact |
|----------|--------|--------|--------|
| **P0** | **Install actual cron jobs** — currently documented but not scheduled | 30 min | **Critical** |
| **P0** | **Create `.learnings/` directory** with ERRORS.md, LEARNINGS.md, FEATURE_REQUESTS.md | 15 min | High |
| **P1** | **Backfill today's 9 errors** with structured IDs and recovery steps | 30 min | High |
| **P1** | **Add "Multi-Agent Learnings" to AGENTS.md** for shared startup context | 20 min | High |
| **P1** | **Add timing wrappers** to graphify/wiki operations for PERFORMANCE.md | 30 min | Medium |

---

## For Obsidian Integration

The `.learnings/` files are markdown with structured headers — **perfect for Obsidian**:
- Use tags: `#learning #error #performance`
- Use Dataview plugin to query by priority/status/area
- Use backlinks to connect related entries
- Graph view shows knowledge compounding over time

---

## Conclusion

The self-improving skill doesn't replace any existing system — it **sits between them** as a structured buffer. Raw experience → `.learnings/` → Review → Promote → Better next session.

**Without it:** Good insights stay scattered or get lost.  
**With it:** The system gets smarter every session.

---

*Report compiled from 4 specialized agent analyses on 2026-05-09.*
