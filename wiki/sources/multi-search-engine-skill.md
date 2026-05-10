---
title: "Multi Search Engine Skill Analysis"
type: source
created: 2026-05-09
updated: 2026-05-10
tags: [source, search-engine, skill, clawhub, web-search]
status: stable
source_refs: [multi-search-engine-skill.md]
related:
  - [[Security Assessment: Multi-Search-Engine Skill]]
  - [[Brave Search API]]
  - [[Hybrid Search]]
  - [[DuckDuckGo]]
---

# Multi Search Engine Skill Analysis

## Source

`raw/multi-search-engine-skill.md` — Initial analysis of the ClawHub skill.

## Summary

A skill integrating 16 search engines (7 domestic Chinese, 9 international) for web crawling without API keys. Uses `web_fetch` with dynamic cookie management, rate limiting, and language-based routing.

## Architecture

### 16 Search Engines

**Domestic (7):** Baidu, Bing CN, Bing INT, 360, Sogou, WeChat Articles, Shenma  
**International (9):** Google, Google HK, DuckDuckGo, Yahoo, Startpage, Brave, Ecosia, Qwant, WolframAlpha

### Workflow

1. **Preparation** — Initialize in-memory cookie store
2. **Language Detection** — Route Chinese queries to domestic engines, others to international
3. **Controlled Search** — Rate-limited requests (1–2s delay, 3–4 engines per batch)
4. **Cookie Management** — On-demand acquisition on 403/429, never persisted to disk
5. **Retry Mechanism** — One retry with fresh cookies after 2s delay
6. **Result Aggregation** — Consolidate and summarize findings

## Claimed Features

- No API keys required — uses standard web search URLs
- "Privacy-focused" engine options (DDG, Startpage, Brave, Qwant)
- Rate limiting and "robots.txt respect"
- Memory-only cookies
- Advanced search operators (site:, filetype:, exact match, exclusion, OR)
- Time filters and DDG bangs
- WolframAlpha for math/conversion queries

## Security & Ethics Caveats

> ⚠️ The companion security assessment (`raw/multi-search-engine-security-assessment.md`) found these claims misleading. The skill is explicitly architected to violate Terms of Service at scale, and the privacy benefits of individual engines are negated by the automation pattern.

## Integration Potential (Revised)

Initially assessed as complementary to the knowledge management system, the security review downgraded this to **do not integrate** for the main workspace. If web search is needed, prefer:
- **Brave Search API** — ToS-compliant, free tier, privacy-respecting
- **Manual `web_fetch`** — One-off, targeted, no automation

## Full Analysis

See `raw/multi-search-engine-skill.md` for the original writeup, and `raw/multi-search-engine-security-assessment.md` for the security review.
