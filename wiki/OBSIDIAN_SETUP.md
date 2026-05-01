# Obsidian Setup Guide for OpenClaw Workspace

## Quick Start

1. **Install Obsidian** (if you haven't): https://obsidian.md/download

2. **Open your workspace as a vault:**
   - Open Obsidian
   - Click "Open folder as vault"
   - Select: `~/.openclaw/workspace` (or `/home/user/.openclaw/workspace`)
   - Done — your entire wiki, memory, and research files are now browsable

3. **What you'll see:**
   - `wiki/` — Your compounding knowledge base (with graph view!)
   - `memory/` — Daily chronological logs
   - `research/` — Long-form reports and analyses
   - `tools/` — Scripts and utilities
   - All wikilinks (e.g. `\[\[Page Name\]\]`) are clickable and navigable

## Recommended Plugins

**Core plugins (enable in Settings → Core plugins):**
- Graph view — Visualize your knowledge network
- Backlinks — See which pages link to the current one
- Tags pane — Browse by tag
- Outline — Navigate headings within a page

**Community plugins (Settings → Community plugins → Browse):**
- **Dataview** — Query your vault with SQL-like syntax
  ```dataview
  TABLE type, tags, updated
  FROM "wiki"
  SORT updated DESC
  ```
- **Smart Connections** (optional) — Semantic search within Obsidian
  - If you want local embeddings inside Obsidian (in addition to our sqlite-vec index)

## Graph View

Press `Ctrl+G` (or `Cmd+G` on Mac) to see your knowledge graph.

You'll see:
- **Hub nodes** — pages with many connections (index, overview, key concepts)
- **Clusters** — related concepts grouped together
- **Orphans** — pages with no connections (the lint tool catches these)

This is incredibly useful for spotting gaps in your knowledge base.

## Daily Workflow

1. **Agent does research** → files it in `wiki/analyses/`
2. **You review in Obsidian** → read, add comments, fix anything
3. **Agent ingests new sources** → updates wiki automatically
4. **You explore in Graph view** → discover connections, ask follow-up questions

## Files You Might Want to Pin

- `wiki/index.md` — Master catalog
- `wiki/log.md` — Recent activity
- `MEMORY.md` — Your long-term memory (if loaded in main session)
- `HEARTBEAT.md` — Periodic task checklist

## Mobile

Obsidian has mobile apps (iOS/Android). Sync options:
- **Obsidian Sync** (paid, end-to-end encrypted)
- **Git** — Commit and push from desktop, pull on mobile
- **iCloud/Dropbox/Google Drive** — Simple but less control

For this setup, **git** is the natural choice since your workspace is already version-controlled.

## Tips

- **Ctrl+Click** (or **Cmd+Click**) a wikilink to open in a new pane
- **Ctrl+Hover** to preview a linked page without leaving the current one
- Use `#tags` inline for quick categorization
- The YAML frontmatter at the top of each file is queryable with Dataview
- Daily notes can go in `memory/` with the existing `YYYY-MM-DD.md` format

## See Also
- [[analyses/convergence-implementation]] — How this system works
- [[entities/obsidian-md]] — Obsidian as an agent knowledge base (research)

