---
title: "KB Landscape Research 2026-04"
type: analysis
created: 2026-04-30
updated: 2026-05-01
tags: ["research", "knowledge-bases", "ai-agents"]
sources: ["karpathy-llm-wiki", "obsidian-md", "web-search-kb-landscape"]
---

# KB Landscape Research: AI Agent Knowledge Bases

*Compiled via parallel agent research on Karpathy llm-wiki.md, Obsidian.md,
and general knowledge base landscape. See [[analyses/convergence-implementation]]
for the implementation guide derived from this research.*

## Key Findings

### 1. Compounding Beats Retrieval
Karpathy's core insight: maintaining a structured, cross-referenced wiki
rather than re-deriving structure on every query. This is architecturally sound
and increasingly validated by the industry move toward persistent memory layers.

### 2. Markdown Is Underrated as Agent Format
Plain text + YAML frontmatter + wikilinks gives human readability, machine
parseability, version control, and zero infrastructure. Scale and relational
reasoning gaps are bridgeable with indexing and extraction layers.

### 3. Obsidian Is the Best Human-Agent Shared Interface
File-based model, graph visualization, exploding AI plugin ecosystem.
Best current platform for collaborative human-LLM knowledge work.

### 4. Hybrid Is the Production Default
2026 consensus: vector + graph + structured storage. But the entry point
can be as simple as a git repo of markdown — and for many use cases, that's sufficient.

### 5. Benchmarks Matter
LoCoMo results: full-context ~73%, smart memory layers ~68% with 91% lower
latency and 90% fewer tokens. The gap is small and closing.

### 6. MCP Is the Integration Standard
Model Context Protocol has become the dominant way to give agents tool access
to external systems, including Obsidian vaults.

## Major Tools
| Tool | Approach | Maturity | Stars |
|------|----------|----------|-------|
| Mem0 | Vector + optional graph | Production | ~54K |
| Zep / Graphiti | Temporal knowledge graph | Production | — |
| Letta | Tiered memory (MemGPT) | Production | ~22K |
| Cognee | Graph-vector hybrid | Production | — |
| Smart Connections | Obsidian semantic search | Mature | ~4.8K |

## See Also
- [[concepts/compounding-knowledge]]
- [[entities/obsidian-md]]
- [[entities/mem0]]
- [[entities/letta]]
- [[entities/cognee]]

