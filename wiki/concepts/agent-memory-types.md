---
title: "Agent Memory Types"
type: concept
created: 2026-05-01
updated: 2026-05-01
tags: ["agents", "memory", "architecture"]
---

# Agent Memory Types

Four canonical memory types recognized across the industry (IBM, LangChain, Google).

## Short-Term / Working Memory
- **Function:** Context window contents
- **Storage:** In-context (no external infrastructure)
- **Failure mode:** Context overflow, silent truncation
- **Mitigation:** Summarization, tiered eviction (Letta core/archival/recall)

## Episodic Memory
- **Function:** Past events, interaction history
- **Storage:** Database + retrieval (raw transcripts or summaries)
- **Failure mode:** Raw transcripts expensive; summaries are lossy
- **Mitigation:** Hierarchical summarization (MemGPT-style)

## Semantic Memory
- **Function:** Atemporal facts, knowledge base
- **Storage:** Vector DB, graph DB, or structured markdown
- **Failure mode:** Similarity ≠ correctness; embeddings can be stale
- **Mitigation:** Hybrid retrieval, periodic reindexing, graph validation

## Procedural Memory
- **Function:** How to do things, workflows, behavioral patterns
- **Storage:** System prompts, few-shot examples, learned rules
- **Failure mode:** Agent behavioral drift if self-updating without guardrails
- **Mitigation:** Schema documents (like this wiki's SCHEMA.md), human review

## Mapping to This Workspace
| Memory Type | Workspace Implementation |
|-------------|------------------------|
| Short-term | OpenClaw session context window |
| Episodic | `memory/YYYY-MM-DD.md` chronological logs |
| Semantic | `wiki/` — cross-referenced, compounding knowledge |
| Procedural | `AGENTS.md`, `SOUL.md`, `SCHEMA.md` |

## See Also
- [[entities/letta]] — Tiered memory architecture from MemGPT research
- [[entities/mem0]] — Self-improving memory layer
- [[concepts/compounding-knowledge]] — Semantic memory approach

