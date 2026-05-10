---
title: "LLM Wiki Pattern"
type: concept
created: 2026-05-09
updated: 2026-05-09
tags: [concept, llm-wiki, pkm, karpathy, pattern]
status: stable
related:
  - [[Knowledge Graph]]
  - [[Personal Knowledge Management]]
  - [[Graphify (tool)]]
  - [[Andrej Karpathy]]
  - [[Compounding Knowledge]]
---

# LLM Wiki Pattern

## Definition

A knowledge management pattern originated by Andrej Karpathy in April 2026. Instead of using traditional RAG (retrieving raw document chunks on every query), an LLM **incrementally compiles** source documents into a persistent, interlinked markdown wiki.

## Core Philosophy

- **Human curates what goes in** — sources, questions, direction.
- **LLM does all maintenance** — summarizing, cross-referencing, filing, flagging contradictions, updating indexes.
- **The wiki becomes a living artifact** that gets richer with every source added.

## Three-Layer Architecture

| Layer | Purpose | Contents |
|-------|---------|----------|
| **Raw Sources** (`raw/`) | Immutable input | Articles, papers, PDFs, images, datasets |
| **The Wiki** (`wiki/`) | LLM-generated knowledge | Markdown pages with `[[wikilinks]]` and YAML frontmatter |
| **The Schema** (`AGENTS.md`/`CLAUDE.md`) | Configuration & conventions | Defines structure, naming, templates, workflows |

## Core Operations

1. **Ingest** — LLM reads a source, writes a summary, cascades updates across related wiki pages.
2. **Query** — LLM reads `index.md`, finds relevant pages, synthesizes answers with citations.
3. **Lint** — Health check for contradictions, orphan pages, stale claims, missing concepts.

## Relationship to Graphify

The LLM Wiki provides the **narrative layer** that Graphify does not generate. Graphify tells you *what connects to what*; the LLM Wiki tells you *what it means*.
