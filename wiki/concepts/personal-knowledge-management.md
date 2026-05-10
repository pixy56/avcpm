---
title: "Personal Knowledge Management"
type: concept
created: 2026-05-09
updated: 2026-05-09
tags: [concept, pkm, knowledge-management, productivity]
status: stable
related:
  - [[LLM Wiki Pattern]]
  - [[Knowledge Graph]]
  - [[Graphify (tool)]]
  - [[Compounding Knowledge]]
---

# Personal Knowledge Management (PKM)

## Definition

The practice of capturing, organizing, and retrieving personal information, notes, and insights in a systematic way. In an AI-assisted workspace, PKM systems combine human curation with LLM automation.

## PKM Stack in This Workspace

| Component | Tool/Pattern | Role |
|-----------|-------------|------|
| Daily logs | `memory/YYYY-MM-DD.md` | Raw session notes |
| Curated memory | `MEMORY.md` | Long-term distilled wisdom |
| Knowledge graph | **Graphify** | Machine-readable structure |
| Narrative wiki | **LLM Wiki** | Human-readable articles |
| Source inputs | `raw/` | Immutable inputs |
| Browse/visualize | Obsidian | Graph view, backlinks |

## Principles

- **Write it down** — mental notes don't survive session restarts
- **Distill over time** — raw logs → curated memory → wiki articles
- **Compound knowledge** — each source should make the system richer
