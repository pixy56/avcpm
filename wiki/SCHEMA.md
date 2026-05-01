# Wiki Schema

## Directory Structure
- `sources/` — Summaries of raw ingested documents
- `concepts/` — Evergreen concept/term pages
- `analyses/` — One-off investigations and synthesized answers
- `entities/` — People, organizations, products, specific named things

## Page Format
```yaml
---
title: "Page Title"
type: source | concept | analysis | entity | index
created: YYYY-MM-DD
updated: YYYY-MM-DD
sources: ["source-filename.md"]
tags: ["tag1", "tag2"]
---
```

One-line summary here.

## Body content

### Related Pages
- `\[\[example-related-page\]\]` — brief description of relationship

## Ingest Workflow
1. Place raw source in `raw/`
2. Create `sources/<slug>.md` with summary
3. Update/create affected `concepts/` and `entities/` pages
4. Update `index.md`, `glossary.md`, `overview.md`
5. Append to `log.md`

## Query Workflow
1. Read `index.md` to find relevant pages
2. Read those pages
3. Synthesize answer with `\[\[citations-to-source-pages\]\]`
4. File notable answer as `analyses/<slug>.md` if worth keeping

## Lint Workflow (weekly)
1. Check for broken `\[\[wiki-links\]\]`
2. Find orphan pages (no incoming links)
3. Detect contradictions between pages
4. Check for stale `updated:` dates
5. Update `index.md` completeness
