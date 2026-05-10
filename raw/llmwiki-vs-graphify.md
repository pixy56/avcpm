# Comparing LLM Wiki and Graphify for Personal Knowledge Management

## Overview

Two complementary approaches to AI-powered knowledge management have emerged in 2026: **LLM Wiki** (a pattern originated by Andrej Karpathy) and **Graphify** (a tool by Safi Shamsi). Both aim to reduce token waste and improve how LLMs interact with large corpora of information, but they solve different parts of the problem.

## LLM Wiki

**Philosophy:** Human curates what goes in; LLM does all maintenance.

**Structure:** Three-layer architecture:
- `raw/` — immutable source inputs (articles, PDFs, transcripts)
- `wiki/` — LLM-generated markdown with `[[wikilinks]]` and YAML frontmatter
- Schema file (`AGENTS.md`/`CLAUDE.md`) — turns any agent into a wiki maintainer

**Key operations:** Ingest (source → summary → cross-references), Query (index → relevant pages → synthesis), Lint (orphans, contradictions, stale claims).

**Strengths:** Human-readable, narrative-driven, compounding knowledge. Obsidian-compatible.

## Graphify

**Philosophy:** Auto-extract a queryable knowledge graph from any folder of files.

**Structure:** 7-stage pipeline:
1. Detect — scan directory, filter by extension
2. Extract — AST (29 languages) + Whisper (audio/video) + LLM subagents (docs/images)
3. Build graph — NetworkX with confidence tags (EXTRACTED/INFERRED/AMBIGUOUS)
4. Cluster — Leiden community detection (no embeddings)
5. Analyze — god nodes, surprising connections, suggested questions
6. Report — `GRAPH_REPORT.md`
7. Export — HTML, Obsidian, MCP, Neo4j

**Key operations:** Query (BFS/DFS traversal), Path (shortest path between nodes), Explain (plain-language node description).

**Strengths:** Machine-readable, fully automated, handles 29+ languages + multimedia. 71.5× token reduction.

## How They Complement Each Other

| Layer | Tool | Role |
|-------|------|------|
| Raw sources | Both | `raw/` folder |
| Structured graph | **Graphify** | Auto-extracts entities, relationships, clusters |
| Curated narrative | **LLM Wiki** | Human-guided, LLM-maintained articles |
| Agent context | Both | Graphify via `GRAPH_REPORT.md` + MCP; LLM Wiki via schema + `index.md` |
| Browse/visualize | Both | Obsidian |

**Graphify is the auto-indexer; LLM Wiki is the auto-author.** Use Graphify to find *what connects to what*, use the wiki to understand *what it means*.

## Recommendation

For a personal OpenClaw workspace:
1. Install Graphify for automatic indexing of code, docs, and media
2. Adopt the LLM Wiki pattern for curated, narrative knowledge
3. Use both together — the graph provides structure, the wiki provides meaning
