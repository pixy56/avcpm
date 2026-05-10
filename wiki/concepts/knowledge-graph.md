---
title: "Knowledge Graph"
type: concept
created: 2026-05-09
updated: 2026-05-09
tags: [concept, knowledge-graph, graph, pkm, ai]
status: stable
related:
  - [[LLM Wiki Pattern]]
  - [[Graphify (tool)]]
  - [[Personal Knowledge Management]]
---

# Knowledge Graph

## Definition

A structured representation of information where entities (nodes) and their relationships (edges) are explicitly modeled. In the context of AI and personal knowledge management, knowledge graphs serve as persistent, queryable indexes of a corpus.

## Key Properties

- **Nodes** represent entities: concepts, files, people, functions, data structures
- **Edges** represent relationships: calls, references, citations, similarities
- **Confidence tagging** distinguishes explicit facts from inferences (e.g., Graphify's EXTRACTED / INFERRED / AMBIGUOUS)
- **Community detection** groups related nodes into clusters without requiring embeddings

## Use in This Workspace

- Graphify auto-builds a knowledge graph from the entire workspace
- The graph is stored in `graphify-out/graph.json`
- The agent queries it via BFS/DFS traversal instead of re-reading raw files
- MCP server exposes graph operations as native tools
