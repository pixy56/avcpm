# Automation Layer + Multi-Search-Engine Integration Analysis

**Analyst:** Subagent (analyze-automation-search)  
**Date:** 2026-05-09  
**Scope:** How the multi-search-engine skill (16 engines, zero API keys) can augment the existing automation layer

---

## Executive Summary

The multi-search-engine skill offers **zero-cost, multi-redundant web search** via 16 engines using `web_fetch` with built-in rate limiting and session-isolated cookies. It can improve the automation layer in four ways: **auto-discovery**, **lightweight validation**, **trend monitoring**, and **heartbeat-assisted proactive search**.

However, the current automation layer has a **critical prerequisite**: the 4 claimed cron jobs (`graphify daily`, `wiki ingest 6h`, `log review 6h`, `weekly lint`) are documented in `HEARTBEAT.md` but **not actually installed** ([automation-analysis.md §1.1](automation-analysis.md)). Search automations should be added **only after** these P0 gaps are closed.

**Bottom line:** Auto-discovery is the highest-value, lowest-risk search automation. Full claim validation is blocked on claim-extraction quality and should be deferred.

---

## 1. Current State (Relevant Context)

| Component | Status | Relevance to Search Integration |
|-----------|--------|--------------------------------|
| 4 claimed cron jobs | ❌ Not installed | Must fix before adding search cron |
| Heartbeat | Underutilized | Can host lightweight search-queue checks |
| `.learnings/` directory | ❌ Not created | Should host search discovery queue & trend logs |
| Manual source discovery | Ad-hoc | Search automation replaces this |
| Ollama semantic extraction | Slow (~3-4 min) | Avoid in search pipeline; keep search lightweight |

**Prerequisites before any search automation:**
1. Install the 4 existing cron jobs ([automation-analysis.md §2.1](automation-analysis.md))
2. Create `.learnings/` directory structure
3. Install the multi-search-engine skill from `https://clawhub.ai/gpyangyoujun/multi-search-engine`

---

## 2. Proposed Search Automations

### 2.1 Auto-Discovery Cron (Priority: 🟡 P1 — Implement First)

**Problem:** Sources are manually discovered and placed in `raw/`. No systematic way to find new relevant content.

**Proposed Job:** `search-auto-discovery` — runs 3×/week (Mon/Wed/Fri)

**Inputs:**
- `wiki/topics-of-interest.md` — one topic per line (e.g., "OpenClaw architecture", "local LLM deployment", "knowledge graph construction")
- Optional: `wiki/trusted-domains.md` — domains to prioritize via `site:` operators

**Process:**
1. Read topics list
2. For each topic, run multi-search-engine with `past month` filter
3. Query 3 engines only (DuckDuckGo, Brave, Google) to limit runtime
4. Collect top 3 results per engine = ~9 candidates per topic
5. **Deduplicate** by URL
6. **Skip if already ingested:** check against `raw/` filenames and `wiki/` slugs
7. Append survivors to `wiki/auto-discovery-queue.md`:
   ```markdown
   - [ ] 2026-05-09 | OpenClaw architecture | https://... | "Title" | Brave
   ```

**Runtime estimate:** 3 topics × 3 engines × 2s delay = ~20s search + 1m agent overhead = **~2 min total**

**Human touchpoint:** Review queue weekly, check items you want ingested, run ingest workflow.

**Value:** High. Systematic coverage across engines reduces blind spots. Zero API cost.

**Risk:** Medium. Search engines change HTML; with 3 engines queried, 1-2 may break but pipeline continues.

---

### 2.2 Lightweight Source Validation (Priority: 🟢 P2 — After Auto-Discovery)

**Problem:** Wiki pages cite sources, but those sources may go stale, move, or be superseded. Full claim extraction is too hard; source vitality checking is tractable.

**Proposed Job:** `wiki-source-vitality` — runs weekly

**Process:**
1. Scan `wiki/` for pages tagged `<!-- validate-sources -->` or listed in `wiki/pages-requiring-validation.md`
2. For each page, extract its title + cited external URLs
3. Search for the page title + key terms across 2 engines
4. Check if cited URLs still appear in top 20 results
5. Flag:
   - `stale-source` — cited URL no longer ranks for the topic
   - `fresh-source-available` — new highly-relevant result not in wiki
6. Write to `.learnings/wiki-validation.md`

**Why this works:** It avoids natural language claim extraction (which is error-prone and slow). It treats search ranking as a proxy for source vitality.

**Value:** Medium. Catches obviously stale references without heavy NLP.

**Risk:** Low. Non-destructive; just flags pages for human review.

---

### 2.3 Trend Monitoring (Priority: 🟢 P2 — After Auto-Discovery)

**Problem:** No tracking of how topics evolve. New developments are only noticed when manually browsing.

**Proposed Job:** `trend-monitor` — runs weekly (Sunday)

**Process:**
1. Read `wiki/topics-of-interest.md`
2. For each topic, search `past week` using 2 engines
3. Save top 10 URLs + titles to `wiki/trends/<topic>-YYYY-MM-DD.md`
4. Compare with previous week's file (simple set diff)
5. Generate a 3-bullet delta summary:
   - New domains not seen before
   - New angles/subtopics
   - Notable authors/organizations
6. Append summary to `memory/YYYY-MM-DD.md`

**Persistent state:** `wiki/trends/` directory holds historical snapshots.

**Value:** Medium. Useful for research-oriented workflows and keeping MEMORY.md current.

**Risk:** Medium. Search result volatility means some "trends" are just SEO noise. Mitigation: require same domain/author to appear 2+ weeks before flagging as meaningful.

---

### 2.4 Search-Assisted Heartbeat (Priority: 🟡 P1 — Quick Win)

**Problem:** Heartbeat is underutilized. It could check search automation state without performing actual searches.

**Proposed Heartbeat Additions:**
1. **Queue health check** — If `wiki/auto-discovery-queue.md` has >10 unchecked items OR oldest item >7 days, surface: "Discovery queue has N pending items. Consider reviewing."
2. **Staleness check** — If no search cron run recorded in `.learnings/CRON_LOG.md` in >7 days, surface: "Auto-discovery hasn't run in N days. Check cron status."
3. **Trend alert** — If `wiki/trends/` shows a topic with >5 new domains this week, surface: "Notable activity detected in [topic]."

**Implementation:** These are **file reads only** — no actual searching during heartbeat. Keeps heartbeat fast and cheap.

**Value:** Medium. Bridges the gap between cron automation and user awareness.

**Risk:** Low. Read-only checks.

---

## 3. Integration Architecture

### 3.1 File Layout (extends [automation-analysis.md §3.1](automation-analysis.md))

```
workspace/
├── .learnings/
│   ├── ERRORS.md
│   ├── CRON_LOG.md
│   └── SEARCH_LOG.md          # NEW: Search cron execution log
├── wiki/
│   ├── auto-discovery-queue.md   # NEW: Pending sources for human review
│   ├── topics-of-interest.md     # NEW: Tracked search topics
│   ├── trusted-domains.md        # NEW: Optional domain whitelist
│   └── trends/                   # NEW: Historical trend snapshots
│       ├── openclaw-architecture-2026-05-01.md
│       └── openclaw-architecture-2026-05-08.md
├── raw/
├── memory/
└── HEARTBEAT.md
```

### 3.2 Cron Job Sequence (after P0 fix)

```
Daily 04:00  → graphify update . (existing)
Every 6h     → raw-check-ingest (existing)
Every 6h     → wiki-log-review (existing)
Weekly Sun   → wiki-weekly-lint (existing)
Mon/Wed/Fri  → search-auto-discovery (NEW)
Weekly Sun   → wiki-source-vitality (NEW, P2)
Weekly Sun   → trend-monitor (NEW, P2)
```

### 3.3 Agent Prompt Design (for search cron jobs)

To keep LLM costs minimal, search cron jobs should use **narrow prompts with structured output**:

```
You are a search automation agent. Follow the multi-search-engine skill.

TASK: Search for "{topic}" using DuckDuckGo, Brave, and Google.
FILTERS: past month
FOR EACH result, extract: URL, title, engine
OUTPUT: JSON array only. No analysis. No summary.
```

This minimizes tokens by avoiding open-ended reasoning. The wrapper script handles deduplication and queue writing.

---

## 4. Cost / Complexity Analysis

| Dimension | Manual (Current) | Multi-Search-Engine Automated |
|-----------|------------------|-------------------------------|
| **API cost** | $0 | $0 (no API keys required) |
| **LLM cost** | $0 | ~$0.01–0.05 per run (narrow prompt, minimal reasoning) |
| **Human time** | 30–60 min/week hunting sources | 5–10 min/week reviewing queue |
| **Coverage** | Spotty, biased by attention | Systematic, 3-engine cross-section |
| **Freshness** | When remembered | Scheduled, consistent |
| **Noise** | Low (human curated) | Medium (requires deduplication + filtering) |
| **Maintenance** | None | Low (skill may need updates if engine HTML changes) |

### Complexity Breakdown

| Automation | Complexity | Why |
|------------|-----------|-----|
| Search-assisted heartbeat | **Low** | File reads only |
| Auto-discovery cron | **Medium** | Search + dedup + queue management |
| Trend monitoring | **Medium-High** | Persistent state + diffing logic |
| Source vitality | **Medium** | Search + URL matching |
| Full claim validation | **Very High** | NLP claim extraction (deferred) |

### Key Cost Advantage

Unlike search APIs (Google Custom Search, SerpAPI, etc.) that charge per query, multi-search-engine uses **web scraping with `web_fetch`**. The only cost is agent session time. For narrow, structured tasks, this is negligible.

---

## 5. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **Search engine HTML changes** break scrapers | Medium | Medium | Use 3 engines per query; if 1 breaks, 2 continue. Monitor `SEARCH_LOG.md` for empty result sets. |
| **Rate limiting / IP blocking** | Low | High | Respect skill's built-in 1-2s delay. For cron, use 2-3s. Rotate User-Agent if needed. |
| **Noise / low-quality results** | High | Low | `site:` filters for trusted domains. Require results to contain topic keywords. Human review of queue. |
| **Duplicate accumulation** | Medium | Medium | Check against `raw/` and `wiki/` before queueing. Periodically prune queue >30 days old. |
| **LLM cost creep** from deep analysis | Low | Medium | Enforce narrow prompts. No open-ended reasoning in search cron. |
| **Cron proliferation** | Medium | Low | Consolidate auto-discovery + trend monitor into a single `search-orchestrator` cron if desired. |

---

## 6. Priority Rankings & Roadmap

### Phase 0: Prerequisites (Do First)

| # | Action | Priority | Effort | Blocks |
|---|--------|----------|--------|--------|
| 0.1 | Install the 4 existing cron jobs ([automation-analysis.md](automation-analysis.md)) | 🔴 P0 | 30 min | Everything |
| 0.2 | Create `.learnings/` directory + `SEARCH_LOG.md` | 🔴 P0 | 10 min | Search automations |
| 0.3 | Install multi-search-engine skill | 🔴 P0 | 5 min | Search automations |
| 0.4 | Create `wiki/topics-of-interest.md` with 3–5 initial topics | 🟡 P1 | 10 min | Auto-discovery, trends |

### Phase 1: Core Search Automation (This Week)

| # | Action | Priority | Effort | Impact |
|---|--------|----------|--------|--------|
| 1.1 | **Search-assisted heartbeat** — add queue/staleness checks to `HEARTBEAT.md` | 🟡 P1 | 15 min | Medium |
| 1.2 | **Auto-discovery cron** — 3×/week search, dedup, queue | 🟡 P1 | 45 min | **High** |
| 1.3 | Create `wiki/auto-discovery-queue.md` template | 🟡 P1 | 5 min | Medium |
| 1.4 | Add search cron timing to `.learnings/PERFORMANCE.md` | 🟡 P1 | 10 min | Medium |

### Phase 2: Enrichment (Next 2 Weeks)

| # | Action | Priority | Effort | Impact |
|---|--------|----------|--------|--------|
| 2.1 | **Trend monitoring** — weekly snapshots + delta reports | 🟢 P2 | 1 hr | Medium |
| 2.2 | **Source vitality** — weekly citation health checks | 🟢 P2 | 45 min | Medium |
| 2.3 | Add `wiki/trusted-domains.md` and `site:` filters | 🟢 P2 | 15 min | Medium |

### Phase 3: Advanced (Deferred)

| # | Action | Priority | Effort | Impact |
|---|--------|----------|--------|--------|
| 3.1 | **Full claim validation** — NLP claim extraction + cross-reference | 🔴 P3 | 4+ hrs | High (if tractable) |
| 3.2 | Semantic deduplication (Ollama-based) of search results | 🔴 P3 | 2 hrs | Low |

---

## 7. Quick Wins (Do Today)

1. **Create `wiki/topics-of-interest.md`** — list 3–5 topics you care about. This is the seed for all search automation.
2. **Add search-queue check to heartbeat** — 3 lines in `HEARTBEAT.md`: check if `wiki/auto-discovery-queue.md` exists and has pending items.
3. **Install multi-search-engine skill** — one command to add it to the skills directory.
4. **Manual trial run** — ask the agent to search one topic using multi-search-engine and save results to `wiki/auto-discovery-queue.md`. This validates the skill works and establishes the output format.

---

## 8. Open Questions

1. **Agent runtime cost** — What is the actual token cost of a narrow-prompt search cron run? Should we measure this during the trial run?
2. **Cron vs. OpenClaw scheduler** — Should search automations use system `crontab` or OpenClaw's native task scheduler? The existing 4 jobs need the same decision.
3. **Queue ownership** — Should the auto-discovery cron also auto-ingest high-confidence items, or keep 100% human review?
4. **Topic list governance** — Who maintains `wiki/topics-of-interest.md`? Should heartbeat suggest retiring topics with no new results after N weeks?

---

*End of analysis. Ready for implementation planning.*
