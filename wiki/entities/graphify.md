---
title: "Graphify"
type: entity
created: 2026-05-09
updated: 2026-05-09
tags: [entity, tool, graphify, knowledge-graph, pkm]
status: stable
related:
  - [[LLM Wiki Pattern]]
  - [[Knowledge Graph]]
  - [[Personal Knowledge Management]]
  - [[Safi Shamsi]]
---

# Graphify

## Overview

Open-source (MIT) AI coding-assistant skill created by **Safi Shamsi**. Converts any folder of code, docs, PDFs, images, videos, or audio into a **queryable knowledge graph**.

## Key Stats

- ~36k GitHub stars (as of May 2026)
- **71.5× token reduction** vs. naive file-reading
- Launched April 2026

## Architecture

7-stage pipeline:
1. **Detect** — scan directory, filter by extension
2. **Extract** — AST (29 languages) + Whisper (audio/video) + LLM subagents (docs/images)
3. **Build Graph** — NetworkX with confidence tags: EXTRACTED / INFERRED / AMBIGUOUS
4. **Cluster** — Leiden community detection (no embeddings, no vector DB)
5. **Analyze** — god nodes, surprising connections, suggested questions
6. **Report** — `GRAPH_REPORT.md`
7. **Export** — HTML, Obsidian vault, MCP server, Neo4j, GraphML

## OpenClaw Integration

- `graphify install --platform claw` — writes rules to `AGENTS.md`
- MCP server — exposes `graph_query`, `graph_path`, `graph_explain` as native tools
- `graphify update .` — incremental AST-only rebuild (no API cost)

## Relationship to LLM Wiki

Graphify provides the **machine-readable graph**; the LLM Wiki provides the **human-readable narrative**. Use both together in a workspace.
