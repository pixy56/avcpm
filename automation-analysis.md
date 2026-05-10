# Automation Layer Analysis: Self-Improving Agent Skill Integration

**Analyst:** Subagent (analyze-automation)  
**Date:** 2026-05-09  
**Scope:** Cron jobs, heartbeat, error recovery, performance tracking

---

## 1. Current Automation State

### 1.1 Cron Jobs (Claimed vs. Reality)

| Claimed Job | Status | Evidence |
|-------------|--------|----------|
| `graphify daily` | ❌ **Not installed** | No crontab for user; not in `/etc/cron.d`; `HEARTBEAT.md` says "scheduled" but no cron entry found |
| `wiki ingest 6-hourly` | ❌ **Not installed** | Same — listed in HEARTBEAT.md but not in any cron table |
| `log review 6-hourly` | ❌ **Not installed** | Same |
| `weekly lint` | ❌ **Not installed** | Same |

**Finding:** The 4 cron jobs exist as *intentions* in `HEARTBEAT.md` but are **not actually scheduled**. Only the system-default `anacron`, `apt-compat`, `logrotate` jobs exist. The wiki log (`wiki/log.md`) shows manual runs of graphify and lint, not automated ones.

**Risk:** Silent failure — the user thinks automation is running, but nothing fires automatically.

### 1.2 Heartbeat

- `HEARTBEAT.md` exists but contains mostly unchecked boxes
- Actual heartbeat checks are minimal (wiki maintenance items checked, but regular checks like email/calendar/weather are unchecked)
- The note says: "Keep this file empty (or with only comments) to skip heartbeat API calls"
- No `memory/heartbeat-state.json` found

**Finding:** Heartbeat is underutilized. It could be doing periodic log reviews and self-diagnosis but currently isn't.

### 1.3 Subagent Timeouts

- Timeout: 16 tool calls / 2 minutes
- Evidence in memory files: multiple "request timed out" entries (`2026-04-19-request-timed-out-before-a-res.md`, `2026-04-20-request-timed-out-before-a-res.md`)
- No structured tracking of which tasks hit limits

### 1.4 Performance Issues

- **Ollama semantic extraction:** Confirmed slow (minutes per run) — `qwen3.6:35b` model via Ollama
- **Graphify:** `graphify update .` is AST-only (no API cost) for daily runs, but semantic extraction is triggered manually and is slow
- **Search index:** `.vault-search.db` exists (1.6MB) but no auto-reindex on file changes — requires manual `search-vault.py index`

---

## 2. How Self-Improving Agent Skill Addresses Each Gap

### 2.1 Cron Job Reliability (Priority: 🔴 CRITICAL)

**Current Problem:**
- Jobs are documented but not scheduled
- No failure logging when jobs don't run
- No distinction between "I scheduled this" and "this actually runs"

**Self-Improving Skill Application:**

```
.learnings/ERRORS.md
└── [ERR-20260509-001] Cron job scheduling gap
    Priority: critical
    Status: pending
    Area: infra
    Summary: 4 cron jobs claimed in HEARTBEAT.md but not installed in crontab
    Details: graphify daily, wiki ingest 6h, log review 6h, weekly lint
             listed as done but no system cron entries found
    Suggested Action: Create actual crontab entries or OpenClaw cron jobs;
                      add verification step to HEARTBEAT.md checks
    Resolution Log: (to be filled when fixed)
```

**Recommendations:**

| # | Action | Priority |
|---|--------|----------|
| 1 | **Install actual cron jobs** — either via `crontab -e` or OpenClaw's task scheduler | 🔴 P0 |
| 2 | Add a "cron verification" heartbeat check that runs weekly and confirms all expected jobs exist in `crontab -l` | 🔴 P0 |
| 3 | Log every cron run to `.learnings/CRON_LOG.md` with exit code and duration | 🟡 P1 |
| 4 | When a cron job fails, create an `[ERR-...]` entry automatically in `.learnings/ERRORS.md` | 🟡 P1 |

**Integration with self-improving skill:**
- The `.learnings/ERRORS.md` becomes the canonical failure log
- On each cron run, append success/failure
- On heartbeat, scan for `[ERR-*]` entries with `status: pending` and surface them

---

### 2.2 Heartbeat Effectiveness (Priority: 🟡 HIGH)

**Current Problem:**
- `HEARTBEAT.md` is a static checklist, not a dynamic tracker
- No record of *when* checks last ran or *what they found*
- Unchecked items (email, calendar, weather) never get attention
- No mechanism to retire checks that aren't useful

**Self-Improving Skill Application:**

**Proposed HEARTBEAT.md refactor:**

```markdown
## Active Checks (rotating, last updated from .learnings/)

| Check | Last Run | Finding | Useful? |
|-------|----------|---------|---------|
| Wiki log review | 2026-05-09 14:00 | 2 pending ingests | yes |
| Email inbox | never | — | **unknown** → evaluate |
| Calendar | never | — | **unknown** → evaluate |

## Retired Checks
- Weather (retired 2026-05-08: not relevant for current work pattern)
```

**Recommendations:**

| # | Action | Priority |
|---|--------|----------|
| 1 | Create `.learnings/HEARTBEAT_EVAL.md` — log each heartbeat check result with timestamp and usefulness rating | 🟡 P1 |
| 2 | After 2 weeks of logging, review which checks find actionable items >20% of the time; retire the rest | 🟡 P2 |
| 3 | Use heartbeat to scan `.learnings/ERRORS.md` for `pending` items and surface them proactively | 🟡 P1 |
| 4 | Add "learning promotion" to heartbeat: if a pending learning is >7 days old, suggest promoting to MEMORY.md or AGENTS.md | 🟢 P2 |

---

### 2.3 Error Recovery Patterns (Priority: 🟡 HIGH)

**Current Problem:**
- Timeout errors exist in memory files but are unstructured
- No recovery playbook: when graphify fails, what do we do?
- No categorization of failures (infra vs. model vs. config vs. transient)
- Same errors likely recur because patterns aren't extracted

**Self-Improving Skill Application:**

**Example `.learnings/ERRORS.md` entry:**

```markdown
## [ERR-20260420-001] Subagent timeout on code review
- Priority: high
- Status: resolved
- Area: infra
- Summary: Code review subagent timed out after 16 tool calls / 2 minutes
- Details: AVCPM architecture review; 17,000-word report required 4 subagents
           spawned sequentially. First agent timed out during deep analysis.
- Root Cause: 16-tool-call limit insufficient for large-codebase deep reviews
- Recovery Action: Split large reviews into focused subagents (architecture,
                   security, performance, testing) with narrower scopes.
- Prevention: For reviews >10k lines, always pre-scope into 4+ subagents.
- Promoted To: AGENTS.md § "Large Code Reviews" (added 2026-05-09)
```

**Recommendations:**

| # | Action | Priority |
|---|--------|----------|
| 1 | Create `.learnings/` directory with `ERRORS.md`, `LEARNINGS.md`, `FEATURE_REQUESTS.md` | 🟡 P1 |
| 2 | Define 3 recovery patterns: **Retry** (transient), **Split** (too big), **Reroute** (wrong tool), **Escalate** (unknown) | 🟡 P1 |
| 3 | On any tool timeout or failure, subagent should log to `ERRORS.md` before dying | 🟡 P1 |
| 4 | Weekly cron: scan `ERRORS.md` for patterns (same error >2x = systemic issue) | 🟢 P2 |

---

### 2.4 Performance Tracking (Priority: 🟡 HIGH)

**Current Problem:**
- Ollama slowness is anecdotal ("minutes per run") but not measured
- Search index reindex time unknown
- No tracking of which operations are getting slower over time
- No alerting when a job exceeds expected duration

**Self-Improving Skill Application:**

**Proposed `.learnings/PERFORMANCE.md`:**

```markdown
## Performance Baselines

| Operation | Baseline | Last Run | Trend | Alert Threshold |
|-----------|----------|----------|-------|-----------------|
| Graphify AST update | 5s | 5s | stable | >30s |
| Graphify semantic extract | 180s | 240s | 🔴 worsening | >300s |
| Search index rebuild | 10s | 12s | stable | >60s |
| Wiki lint | 2s | 2s | stable | >10s |
```

**Recommendations:**

| # | Action | Priority |
|---|--------|----------|
| 1 | Add timing wrappers to all cron jobs and log to `.learnings/PERFORMANCE.md` | 🟡 P1 |
| 2 | Set alert thresholds: if graphify semantic >5 min, downgrade to AST-only and flag for investigation | 🟡 P1 |
| 3 | For Ollama: track per-model latency (`qwen3.6:35b` vs alternatives); if >10 min, consider switching model or batching | 🟢 P2 |
| 4 | **Auto-reindex on file change**: Use `inotifywait` or filesystem watcher to trigger `search-vault.py index` when `.md` files change, rather than periodic full reindex | 🟡 P1 |

---

## 3. Integration Architecture

### 3.1 File Layout

```
workspace/
├── .learnings/
│   ├── ERRORS.md          # Failure log with recovery patterns
│   ├── LEARNINGS.md       # Corrections, insights, best practices
│   ├── FEATURE_REQUESTS.md # User requests + automation gaps
│   ├── CRON_LOG.md        # Structured cron execution log
│   ├── HEARTBEAT_EVAL.md  # Check usefulness tracking
│   └── PERFORMANCE.md     # Timing baselines and trends
├── memory/
│   └── (daily notes as before)
├── HEARTBEAT.md           # Refactored: checklist + dynamic state
└── MEMORY.md              # Curated wisdom (promoted from .learnings/)
```

### 3.2 Promotion Flow

```
Tool failure / Insight / Timeout
    ↓
[Log to .learnings/*.md with ID]
    ↓
Heartbeat scan (weekly) or Cron review (weekly)
    ↓
Pattern detected? (same error >1x, insight validated)
    ↓
Promote to AGENTS.md / SOUL.md / TOOLS.md / MEMORY.md
    ↓
Mark original entry `status: promoted`
```

### 3.3 Cron Job Re-implementation (with self-improving hooks)

```bash
# ~/.openclaw/cron/ (new directory for all automation scripts)

# run-graphify.sh
#!/bin/bash
START=$(date +%s)
LOG="$HOME/.openclaw/workspace/.learnings/CRON_LOG.md"
ERR="$HOME/.openclaw/workspace/.learnings/ERRORS.md"

echo "## [CRON] graphify update $(date -Iseconds)" >> "$LOG"
if graphify update . >> "$LOG" 2>&1; then
    DURATION=$(($(date +%s) - START))
    echo "- Status: success (${DURATION}s)" >> "$LOG"
    # Update PERFORMANCE.md
else
    echo "- Status: FAILED" >> "$LOG"
    echo "## [ERR-$(date +%Y%m%d)-XXX] graphify update failed" >> "$ERR"
    # Alert via heartbeat next run
fi
```

---

## 4. Priority Rankings

| Priority | Area | Action | Impact | Effort |
|----------|------|--------|--------|--------|
| **🔴 P0** | Cron | Install the 4 claimed cron jobs | High | 30 min |
| **🔴 P0** | Cron | Add cron self-verification to heartbeat | High | 15 min |
| **🟡 P1** | Errors | Create `.learnings/` directory and `ERRORS.md` | High | 20 min |
| **🟡 P1** | Errors | Define 4 recovery patterns + log on failure | High | 30 min |
| **🟡 P1** | Performance | Add timing wrappers + `PERFORMANCE.md` | Medium | 30 min |
| **🟡 P1** | Performance | Implement auto-reindex on file change | Medium | 45 min |
| **🟡 P1** | Heartbeat | Refactor to dynamic check tracking | Medium | 30 min |
| **🟢 P2** | Heartbeat | Weekly learning promotion sweep | Low | 20 min |
| **🟢 P2** | Errors | Weekly error pattern analysis cron | Low | 30 min |
| **🟢 P2** | Performance | Ollama model latency comparison | Low | 1 hr |

---

## 5. Quick Wins (Do This Week)

1. **Create `.learnings/`** with the 5 markdown files — low effort, high structure
2. **Write the 4 cron job scripts** and actually install them with `crontab -e`
3. **Add one error entry** for the timeout pattern (copy from memory files)
4. **Add timing to the next manual graphify run** to establish baseline
5. **Update `HEARTBEAT.md`** to check `.learnings/ERRORS.md` for pending items

---

## 6. Open Questions

1. Are cron jobs intended to be system-level (`/etc/cron.d/`) or user-level (`crontab -e`)?
2. Is there an OpenClaw-native task scheduler that should be used instead of cron?
3. What is the acceptable downtime for search index staleness? (determines reindex strategy)
4. Should failed cron jobs alert via heartbeat, or via a different channel?

---

*End of analysis. Ready for implementation planning.*
