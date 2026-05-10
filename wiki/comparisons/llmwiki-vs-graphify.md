---
title: "LLM Wiki vs Graphify"
type: comparison
created: 2026-05-09
updated: 2026-05-09
tags: [comparison, llm-wiki, graphify, pkm]
status: stable
related:
  - [[LLM Wiki Pattern]]
  - [[Graphify (tool)]]
  - [[Personal Knowledge Management]]
  - [[Knowledge Graph]]
---

# LLM Wiki vs Graphify

## At a Glance

| Aspect | LLM Wiki | Graphify |
|--------|----------|----------|
| **Type** | Pattern / methodology | Tool / pipeline |
| **Origin** | Andrej Karpathy (April 2026) | Safi Shamsi (April 2026) |
| **Automation** | LLM maintains wiki pages | Full auto-extraction from files |
| **Human role** | Curates sources, sets direction | Minimal — mostly hands-off |
| **Output format** | Markdown with `[[wikilinks]]` | NetworkX graph + reports |
| **Languages supported** | Any (text-based) | 29 programming languages + docs/media |
| **Token reduction** | Moderate (avoids re-summarizing) | 71.5× vs naive file-reading |
| **Obsidian support** | Native | Vault export available |
| **Confidence tracking** | Implicit (human review) | Explicit (EXTRACTED/INFERRED/AMBIGUOUS) |

## When to Use Which

| Scenario | Best Tool |
|----------|-----------|
| Deep narrative understanding | **LLM Wiki** |
| Quick "what connects to what" | **Graphify** |
| Codebase navigation | **Graphify** |
| Research synthesis & comparisons | **LLM Wiki** |
| Multimedia (video, audio, images) | **Graphify** |
| Human-curated quality control | **LLM Wiki** |

## Recommended: Use Both

- Drop files into `raw/`
- Graphify auto-indexes everything into `graphify-out/graph.json`
- LLM Wiki ingests key sources into narrative `wiki/` pages
- Agent queries the graph for structure, reads the wiki for meaning
