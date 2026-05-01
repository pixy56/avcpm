---
title: "Compounding Knowledge"
type: concept
created: 2026-05-01
updated: 2026-05-01
tags: ["knowledge-management", "llm", "pattern"]
sources: ["karpathy-llm-wiki"]
---

# Compounding Knowledge

Knowledge that is accumulated, cross-referenced, and synthesized such that
each new addition strengthens the existing corpus.

## Contrast with Stateless Retrieval

| Approach | Mechanism | Result |
|----------|-----------|--------|
| **Compounding** | Sources compiled into structured wiki once; cross-references built persistently | Each query benefits from prior synthesis |
| **RAG (Stateless)** | Documents chunked, embedded, retrieved fresh each query | Model re-derives structure every time |

## Key Properties
- Cross-references exist between pages (not recreated per query)
- Contradictions are detected and flagged during lint
- Synthesis reflects the full corpus, not just retrieved chunks
- Knowledge improves with every source added

## Why LLMs Change This
Humans abandon wikis because maintenance burden outpaces value.
LLMs don't get bored and can touch 15 files in one ingest pass.

## See Also
- [[sources/karpathy-llm-wiki]] — Original pattern
- [[concepts/hybrid-search]] — Finding relevant pages at scale
- [[entities/mem0]] — Production memory layer with compounding properties

