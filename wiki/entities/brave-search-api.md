---
title: "Brave Search API"
type: entity
created: 2026-05-10
updated: 2026-05-10
tags: [entity, search-engine, api, privacy, tool]
status: stable
related:
  - [[DuckDuckGo]]
  - [[Multi Search Engine Skill Analysis]]
  - [[Security Assessment: Multi-Search-Engine Skill]]
  - [[Privacy Risk]]
---

# Brave Search API

## Overview

Brave Search API is an official, Terms-of-Service-compliant search API provided by Brave Software. It offers a generous free tier (2,000 queries/month) and is recommended as the primary external search integration for the workspace.

## Why It Was Recommended

The security assessment of the `multi-search-engine` skill concluded that Brave Search API is the **best alternative** for real-time web search in this workspace:

| Feature | Brave Search API | Multi-Search Skill |
|---------|-----------------|-------------------|
| ToS Compliant | ✅ Yes | ❌ No |
| Privacy-Respecting | ✅ Yes | ⚠️ Negated by automation |
| Free Tier | ✅ 2,000 queries/month | ✅ Free (but externalizes cost) |
| API Key Required | ✅ Yes (accountability) | ❌ No (circumvents controls) |
| Rate Limiting | ✅ Built-in | ⚠️ Inadequate |
| Independent Index | ✅ Yes | ❌ Scrapes others |

## Integration

- **Documentation:** https://api.search.brave.com/
- **Use case:** Real-time web data for wiki source discovery, validation of claims
- **Alternative to:** Manual `web_fetch` for one-off lookups

## Related

- [[Security Assessment: Multi-Search-Engine Skill]] — Full comparison and recommendation context
- [[Privacy Risk]] — Privacy risk framework
- [[DuckDuckGo]] — Another privacy-focused engine (but no official API)
