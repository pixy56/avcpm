---
title: "Convergence Implementation Guide"
type: analysis
created: 2026-05-01
updated: 2026-05-01
tags: ["implementation", "guide", "knowledge-base"]
sources: ["kb-landscape-2026-04"]
---

# Convergence Implementation Guide

*Step-by-step build for Matt's OpenClaw workspace. See [[analyses/kb-landscape-2026-04]]
for the research that informed this architecture.*

## Architecture
```
┌─ Agent Layer (OpenClaw) ─┐
│  MCP / CLI / Filesystem    │
├─ Knowledge Layer ─────────┤
│  wiki/ + memory/ (markdown)│
├─ Search Layer ────────────┤
│  sqlite-vec + model2vec    │
├─ Graph Layer (optional) ───┤
│  Cognee / Neo4j            │
└─ Sync Layer ──────────────┘
   git + optional cloud      │
```

## Phase 1: Foundation ✓ COMPLETE
- [x] Create `wiki/{sources,concepts,analyses,entities}/`
- [x] Create `raw/` directory
- [x] Write `SCHEMA.md` — wiki constitution
- [x] Create `index.md`, `log.md`, `overview.md`, `glossary.md`
- [x] Seed concepts: compounding-knowledge, hybrid-search, agent-memory-types
- [x] File analyses: kb-landscape-2026-04, convergence-implementation

## Phase 2: Search Layer (Next)
- [ ] Install `sqlite-vec` + `model2vec`
- [ ] Create `tools/search-vault.py`
- [ ] Index workspace
- [ ] Test search queries

## Phase 3: Graph Layer (Later, 500+ pages)
- [ ] Evaluate Cognee
- [ ] Create `tools/graph-extract.py`
- [ ] Set up Neo4j if needed

## Phase 4: Agent Integration
- [ ] Create `tools/mcp-wiki-ingest.py`
- [ ] Create `tools/wiki-lint.py`
- [ ] Document tools in TOOLS.md
- [ ] Add heartbeat maintenance tasks

## Migration Strategy
- Keep `memory/` as raw chronological notes
- `wiki/` for compiled, cross-referenced knowledge
- Cross-link: `memory/2026-04-30` ↔ `wiki/analyses/kb-landscape-2026-04`
- Unified search index over both directories

## Scaling Triggers
| Scale | Action |
|-------|--------|
| < 100 pages | index.md + ripgrep |
| 100-500 | sqlite-vec search |
| 500+ | Cognee graph |
| Multi-agent | MCP server |
| Temporal queries | Zep/Graphiti |
| Production | Mem0g / Letta backend |

## See Also
- [[concepts/compounding-knowledge]]
- [[concepts/hybrid-search]]
- [[SCHEMA]]

