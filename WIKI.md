# WIKI.md - Workspace Knowledge Wiki Schema

This file defines the structure and conventions for the LLM Wiki in this OpenClaw workspace.

## Philosophy

- **Human curates what goes in** — sources, questions, direction.
- **LLM does all maintenance** — summarizing, cross-referencing, filing, flagging contradictions, updating indexes.
- **The wiki is a living artifact** that gets richer with every source added.
- **Graphify provides the machine-readable graph**; the wiki provides the human-readable narrative.

## Directory Structure

```
wiki/
├── index.md          # Master index: concepts, entities, sources, comparisons
├── log.md            # Changelog of all ingest events
├── concepts/         # Abstract ideas, patterns, definitions
├── entities/         # People, projects, tools, organizations
├── sources/          # Summaries and metadata for raw sources
└── comparisons/      # Side-by-side comparisons (tools, approaches, etc.)
```

## Page Template

Every wiki page must include YAML frontmatter:

```yaml
---
title: "Page Title"
type: concept | entity | source | comparison
created: YYYY-MM-DD
updated: YYYY-MM-DD
tags: []
status: draft | stable | archived
source_refs: []      # For source pages: filenames in raw/
related: []          # Wikilinks to related pages
---
```

## Linking Conventions

- Use `[[Page Name]]` for internal wiki links.
- Use `[[Page Name|display text]]` for aliased links.
- Link liberally — the graph is only useful if it's connected.

## Ingest Workflow

1. **Drop** a new source (article, PDF, transcript, etc.) into `raw/`.
2. **Notify** the agent: "Ingest the new source in raw/."
3. The agent will:
   - Read the source.
   - Write or update a page in `wiki/sources/`.
   - Extract concepts and entities, writing/updating pages in `wiki/concepts/` and `wiki/entities/`.
   - Cross-reference everything with `[[wikilinks]]`.
   - Update `wiki/index.md`.
   - Append a summary to `wiki/log.md`.

## Query Workflow

1. Ask a question.
2. The agent reads `wiki/index.md` to find relevant pages.
3. The agent reads those pages and synthesizes an answer with citations.
4. If the answer is good, the agent may file it back into the wiki as a new concept or comparison.

## Lint Workflow

Run periodically (weekly or on heartbeat):

- Check for **orphan pages** (no incoming links).
- Check for **broken wikilinks**.
- Check for **stale claims** (source updated but wiki not refreshed).
- Check for **missing concepts** (mentioned in sources but no concept page).
- Check for **contradictions** between pages.

## Relationship to Other Workspace Files

| File | Role |
|------|------|
| `AGENTS.md` | Workspace-level agent conventions |
| `MEMORY.md` | Curated long-term personal memory |
| `memory/YYYY-MM-DD.md` | Raw daily session logs |
| `WIKI.md` | **This file** — wiki schema and conventions |
| `raw/` | Immutable source inputs |
| `wiki/` | LLM-generated, human-curated knowledge base |
| `GRAPH_REPORT.md` | Graphify-generated graph summary (machine-readable) |

## Graphify Integration

- Graphify auto-indexes the entire workspace (including `raw/` and `wiki/`).
- `GRAPH_REPORT.md` provides the agent with a machine-readable map of connections.
- The wiki provides narrative context that Graphify does not generate.
- Use both: ask Graphify for "what connects to what," ask the wiki for "what does it mean."
