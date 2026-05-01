---
title: "Hybrid Search"
type: concept
created: 2026-05-01
updated: 2026-05-01
tags: ["search", "vector", "bm25", "retrieval"]
---

# Hybrid Search

Combining multiple retrieval strategies for fast, accurate document search.

## Components

| Layer | Technology | Handles |
|-------|-----------|---------|
| **Keyword** | BM25 / FTS5 / ripgrep | Exact matches, proper nouns, rare terms |
| **Semantic** | Vector embeddings (cosine similarity) | Synonyms, paraphrases, conceptual similarity |
| **Reranking** | Cross-encoder / LLM | Precision: reorder top-k candidates |

## Local Implementation
- `sqlite-vec` for vector storage
- `model2vec` (StaticModel) for lightweight embeddings
- Optional `qmd` for production-grade hybrid + LLM reranking

## Tradeoffs
| Approach | Latency | Accuracy | Setup |
|----------|---------|----------|-------|
| BM25 only | Fast | Low | Trivial |
| Vector only | Medium | Medium | Easy |
| Hybrid BM25+vector | Medium | High | Moderate |
| + LLM reranking | Slow | Highest | Complex |

## See Also
- [[entities/cognee]] — Graph-vector hybrid with 14 retrieval modes
- [[analyses/convergence-implementation]] — Implementation details

