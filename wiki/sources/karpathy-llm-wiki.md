---
title: "Karpathy llm-wiki.md"
type: source
created: 2026-05-01
updated: 2026-05-01
tags: ["pattern", "knowledge-base", "llm"]
---

# Karpathy llm-wiki.md

Original pattern document by Andrej Karpathy (April 2026).
GitHub Gist — 5,000+ stars, 5,000+ forks.

## Core Idea
Instead of stateless retrieval (RAG), the LLM incrementally builds and
maintains a persistent, structured wiki. Knowledge compounds rather than
being re-derived.

## Architecture
- Raw sources (human curated)
- The Wiki (LLM generated: summaries, entities, concepts)
- The Schema (co-evolved configuration)

## Workflows
- **Ingest** — Source → summary → cross-referenced updates
- **Query** — Index → relevant pages → synthesized answer
- **Lint** — Maintenance pass for contradictions, orphans, stale content

## See Also
- [[entities/karpathy-andrej]]
- [[concepts/compounding-knowledge]]
- [[analyses/convergence-implementation]]
