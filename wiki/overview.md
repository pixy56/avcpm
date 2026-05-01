---
title: "Overview"
type: overview
created: 2026-05-01
updated: 2026-05-01
---

# Overview: Matt's AI Agent Knowledge Base

## Purpose
A self-maintaining, compounding knowledge base for Matt's OpenClaw workspace,
following the Karpathy llm-wiki.md pattern and Convergence layered architecture.

## Layers
1. **Raw Sources** (`raw/`) — Immutable ingested documents
2. **Wiki** (`wiki/`) — LLM-compiled, cross-referenced markdown
3. **Memory** (`memory/`) — Chronological daily notes + curated long-term memory
4. **Search Index** (`.vault-search.db`) — Hybrid BM25 + vector for fast retrieval
5. **Graph** (optional, Cognee) — Relational reasoning for complex queries

## Principles
- Human curates sources and asks questions
- LLM handles filing, cross-referencing, and maintenance
- Plain text first — human-readable, git-trackable, portable
- Progressive enhancement — add complexity only when needed

## Current State
Initialized 2026-05-01. Contains research on AI agent knowledge bases,
implementation plans, and foundational concepts.

