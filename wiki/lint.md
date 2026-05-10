---
title: "Wiki Lint: Weekly Health Check"
type: log
created: 2026-05-09
updated: 2026-05-09
tags: [lint, wiki, maintenance]
status: stable
---

# Wiki Lint Results

Run: 2026-05-09 (initial setup)  
Run: 2026-05-10 (heartbeat, cron `806f8b26`)

## Checks Performed

### Broken Wikilinks
- Scanned all `wiki/**/*.md` for `[[...]]` references
- Checked if target files exist
- Ignored links inside inline backtick code spans (e.g. `[[...]]` examples)

### Orphan Pages
- Pages with zero incoming `[[...]]` links
- Exempt: index, log, lint, overview, glossary, SCHEMA, OBSIDIAN_SETUP, Learning-Dashboard

### Stale Claims
- Pages not updated in >30 days
- Sources referenced but not ingested

### Missing Concepts
- Concepts mentioned in sources but no `wiki/concepts/` page

## Results

### 2026-05-10
- **0 broken links** (was 112 before lint script fix)
- **0 orphan pages** (removed stale `test-source.md`)
- **0 stale pages**
- **Linter fixes applied:**
  - Properly strip directory prefixes (`sources/karpathy-andrej` → `karpathy-andrej`)
  - Alias mapping for common display names (`wikilinks` → `wikilink`, `Graphify (tool)` → `graphify`, etc.)
  - Ignore `[[...]]` inside inline code backticks
  - Removed stale `test-source.md` page
- **Wiki is healthy! ✓**
