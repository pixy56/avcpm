# Multi-Search-Engine Integration Report

**Skill:** https://clawhub.ai/gpyangyoujun/multi-search-engine  
**Date:** 2026-05-09  
**Analysts:** 4 specialized agents (Search Integration, Automation, Security, Practicality)

---

## Executive Summary

**Recommendation: REJECT full integration** of the 16-engine scraper. **Adopt selective, lightweight search augmentation** instead.

The skill proposes a complex, high-maintenance web-scraping system (16 engines, dynamic cookies, rate limiting) that violates search engine ToS and introduces significant privacy/security risks. The practical and security analyses are strongly negative.

However, the **research value** identified by the Search Integration and Automation analysts is real. The solution is to use **existing, compliant tools** (`web_search`, `web_fetch`) for the same outcomes without the risks.

---

## Vote Tally

| Analyst | Verdict | Key Concern |
|---------|---------|-------------|
| **Search Integration** | ✅ INTEGRATE (P1) | Source discovery, claim validation, zero API cost |
| **Automation** | ⚠️ CONDITIONAL | Integrate AFTER P0 prerequisites; start small (3 engines, 3×/week) |
| **Security** | ❌ DO NOT | ToS violations, query exposure, untrusted code |
| **Practicality** | ❌ DO NOT | 2-5 hrs/week maintenance, 16 failure points, CAPTCHA risk |

**Consensus: 2 against, 1 conditional, 1 for.** The "for" case acknowledges value but proposes the same outcomes via safer means.

---

## What We Should Do Instead

### P1 — Use Existing `web_search` Tool (Already Available)

**What:** The OpenClaw `web_search` tool (provider-backed, likely Perplexity or Brave) already provides aggregated search results. Use it for:
- Source discovery when concepts are missing
- Cross-validation of wiki claims
- Research augmentation

**Why it's better:**
- ✅ API-backed, stable, ToS-compliant
- ✅ No maintenance burden
- ✅ No privacy leakage (provider handles queries)
- ✅ No CAPTCHA/rate-limit issues
- ✅ Already works (we used it earlier today)

**How:**
```python
# In wiki lint or ingest workflow
web_search("site:github.com OR site:arxiv.org knowledge graph LLM")
web_search("Karpathy LLM wiki pattern")
```

### P2 — Lightweight Auto-Discovery (Conditional)

**What:** After P0 prerequisites (cron jobs actually installed, `.learnings/` stable), add a simple search-augmented cron:
- Run 3×/week
- Query 2-3 privacy engines (DuckDuckGo, Brave) via `web_fetch`
- Dedupe against existing `raw/` and `wiki/`
- Append promising sources to a human-reviewed queue

**Why it's acceptable:**
- Uses `web_fetch` (already a first-class tool)
- Targets privacy engines (explicitly allow scraping)
- Low frequency (3×/week, not 16 engines constantly)
- Human review gate before auto-ingest

### P3 — Document Search Strategies (Immediate)

**What:** Add search strategy documentation to `TOOLS.md` and wiki:
- When to use `web_search` vs `web_fetch`
- Which engines for which queries
- Advanced operators (`site:`, `filetype:`, `"exact match"`)
- Time filters for recency

**Why it's valuable:**
- Zero code, zero maintenance
- Makes existing tools more effective
- Captures institutional knowledge

---

## What We Should NOT Do

| Rejected Approach | Why |
|-------------------|-----|
| Full 16-engine scraper | ToS violations across all engines |
| Dynamic cookie management | Privacy risk, complexity, fragility |
| Rate-limited batch orchestration | 2-5 hrs/week maintenance minimum |
| Auto-ingest without review | Quality risk, spam potential |
| HTML parsing across 16 formats | Brittle, breaks when layouts change |

---

## Specific Risks (from Security Analysis)

| Risk | Severity | Detail |
|------|----------|--------|
| **ToS Violations** | 🔴 HIGH | Scraping 16 search engines without API keys violates every engine's terms |
| **Query Exposure** | 🔴 HIGH | Every query broadcast to 16 third-party servers; current system has zero external exposure |
| **Untrusted Code** | 🟠 MEDIUM-HIGH | ClawHub skill from unknown author; full network access; no code review |
| **Fingerprinting** | 🟡 MEDIUM | Automated patterns trivially detectable; cookies enable session correlation |
| **Rate Limiting** | 🟡 MEDIUM | 1-2s delays insufficient for 16 engines; likely to trigger CAPTCHA/IP blocks |

---

## Comparison: Current vs. Proposed vs. Recommended

| Dimension | Current (Graphify + Ollama) | Proposed (16-engine scraper) | Recommended (web_search + selective web_fetch) |
|-----------|---------------------------|------------------------------|-----------------------------------------------|
| **Data locality** | ✅ All local | ❌ 16 external servers | ⚠️ Provider-dependent (1 external) |
| **Privacy** | ✅ No tracking | ❌ Full query exposure | ✅ Provider handles privacy |
| **ToS compliance** | ✅ No issues | ❌ Violates all engines | ✅ API-backed, compliant |
| **Maintenance** | ✅ Low | ❌ 2-5 hrs/week | ✅ Near-zero |
| **Source discovery** | ❌ Manual only | ✅ Automated | ✅ Semi-automated (cron + review) |
| **Claim validation** | ❌ Internal only | ✅ External consensus | ✅ External consensus |
| **Cost** | ✅ Free (Ollama) | ✅ Free (scraping) | ✅ Free (provider) |

---

## Recommended Action Items

| Priority | Action | Effort | Impact |
|----------|--------|--------|--------|
| **P0** | **Stabilize P0 prerequisites first** — ensure cron jobs actually run, `.learnings/` healthy | 30 min | Critical |
| **P1** | **Document search strategies in TOOLS.md** — `web_search` operators, `web_fetch` patterns | 20 min | High |
| **P1** | **Add `web_search` to wiki lint workflow** — validate stale claims periodically | 30 min | High |
| **P2** | **Create `wiki/topics-of-interest.md`** — track concepts worth researching | 15 min | Medium |
| **P2** | **Lightweight auto-discovery cron** (3×/week, 2 engines, human review) | 1 hr | Medium |
| **P3** | **Evaluate Brave Search API** (2,000 free queries/month, ToS-compliant) | 30 min | Low |
| **❌ REJECTED** | Full 16-engine scraper integration | — | — |

---

## Key Insight

The multi-search-engine skill **solves a real problem** (source discovery, claim validation) but with the **wrong solution** (brittle scraping, ToS violations, high maintenance). The correct approach is to use the **tools we already have** (`web_search`, `web_fetch`) in a **disciplined, documented way**.

The value isn't in the 16-engine complexity — it's in the **research workflow**: identify missing concepts → search → validate → ingest. That workflow works with 1 engine and 3 operators just as well as with 16 engines and cookie rotation.

---

*Report compiled from 4 specialized agent analyses on 2026-05-09.*
