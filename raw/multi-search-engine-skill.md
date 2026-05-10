# Multi Search Engine Skill Analysis

## Source
https://clawhub.ai/gpyangyoujun/multi-search-engine

## Summary

A skill that integrates 16 search engines (7 domestic Chinese, 9 international) for web crawling without API keys. Uses `web_fetch` with dynamic cookie management and rate limiting.

## Architecture

### 16 Search Engines

**Domestic (7):** Baidu, Bing CN, Bing INT, 360, Sogou, WeChat Articles, Shenma
**International (9):** Google, Google HK, DuckDuckGo, Yahoo, Startpage, Brave, Ecosia, Qwant, WolframAlpha

### Workflow

1. **Preparation** — Initialize in-memory cookie store
2. **Language Detection** — Route Chinese queries to domestic engines, others to international
3. **Controlled Search** — Rate-limited requests (1-2s delay, 3-4 engines per batch)
4. **Cookie Management** — On-demand acquisition on 403/429, never persisted to disk
5. **Retry Mechanism** — One retry with fresh cookies after 2s delay
6. **Result Aggregation** — Consolidate and summarize findings

## Key Features

- **No API keys required** — Uses standard web search URLs
- **Privacy-focused** — DuckDuckGo, Startpage, Brave, Qwant options
- **Rate limiting** — Respects server load
- **Cookie hygiene** — Memory-only, cleared after session
- **Advanced operators** — site:, filetype:, exact match, exclusion, OR
- **Time filters** — past hour/day/week/month/year
- **WolframAlpha** — Math, conversion, stock, weather queries
- **DDG Bangs** — !g, !gh, !so, !w, !yt shortcuts

## Integration Potential

This skill complements our knowledge management system:
- **Research augmentation** — Multi-engine search for wiki source material
- **Validation** — Cross-reference wiki claims across engines
- **Discovery** — Find new sources for `raw/` folder
- **No cost** — No API keys needed

## Security & Ethics

- Respects robots.txt and ToS
- Rate limiting built-in
- No personal data collection
- Session-isolated cookies

## Documentation

- references/advanced-search.md — Domestic search guide
- references/international-search.md — International search guide
