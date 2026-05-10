---
title: "DuckDuckGo"
type: entity
created: 2026-05-10
updated: 2026-05-10
tags: [entity, search-engine, privacy, tool]
status: stable
related:
  - [[Brave Search API]]
  - [[Multi Search Engine Skill Analysis]]
  - [[Privacy Risk]]
---

# DuckDuckGo

## Overview

DuckDuckGo is a privacy-focused search engine that does not track users or personalize search results. It aggregates results from various sources including its own crawler (DuckDuckBot), Bing, and Yahoo.

## Privacy Claims

- No user tracking or profiling
- No search history stored
- No ad targeting based on personal data
- HTTPS by default

## API Availability

- **No official API** for general web search
- **DuckDuckGo Instant Answer API** — limited to specific answer types
- HTML scraping is technically possible but violates Terms of Service

## In Multi-Search Context

The `multi-search-engine` skill includes DuckDuckGo as one of its 16 engines, framing it as a "privacy-focused" option. However, the security assessment noted that:
> The privacy benefit of the engine is negated by the automation pattern — queries are still sent in an automated, fingerprintable way.

## Related

- [[Brave Search API]] — Alternative with official API and ToS compliance
- [[Privacy Risk]] — Privacy risk assessment framework
- [[Security Assessment: Multi-Search-Engine Skill]] — Full context
