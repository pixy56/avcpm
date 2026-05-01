# The Convergence Layered System: Implementation Guide
*A practical, step-by-step build for Matt's OpenClaw workspace*

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│  AGENT LAYER (OpenClaw, Claude Code, Codex, etc.)      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐   │
│  │  MCP Server │  │  CLI/REST   │  │  Filesystem I/O │   │
│  │  (Obsidian) │  │  (obsidian) │  │  (direct md)    │   │
│  └──────┬──────┘  └──────┬──────┘  └────────┬────────┘   │
│         └─────────────────┼────────────────────┘            │
│                           ▼                               │
│  ┌─────────────────────────────────────────────────────┐ │
│  │  KNOWLEDGE LAYER (Markdown Vault + Frontmatter)     │ │
│  │  wiki/                    memory/                   │ │
│  │  ├── index.md             ├── YYYY-MM-DD.md          │ │
│  │  ├── log.md               └── MEMORY.md             │ │
│  │  ├── overview.md                                      │ │
│  │  ├── glossary.md                                      │ │
│  │  ├── sources/                                         │ │
│  │  ├── concepts/                                        │ │
│  │  └── analyses/                                        │ │
│  └─────────────────────────────────────────────────────┘ │
│                           │                               │
│         ┌─────────────────┼────────────────────┐         │
│         ▼                 ▼                    ▼         │
│  ┌──────────────┐  ┌─────────────┐  ┌─────────────────┐ │
│  │ SEARCH LAYER │  │ GRAPH LAYER │  │  SYNC LAYER     │ │
│  │ qmd / BM25   │  │ (optional)  │  │  git + sync     │ │
│  │ + sqlite-vec │  │ cognee /    │  │  (optional)     │ │
│  │              │  │ neo4j       │  │                 │ │
│  └──────────────┘  └─────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

---

## Phase 1: Foundation — Markdown Wiki (Days 1–2)

### 1.1 Create the Wiki Structure

In your existing workspace (`/home/user/.openclaw/workspace/`):

```bash
mkdir -p wiki/{sources,concepts,analyses,entities}
touch wiki/index.md wiki/log.md wiki/overview.md wiki/glossary.md
```

### 1.2 Create the Schema Document (`wiki/SCHEMA.md`)

This is your "constitution" — the LLM reads this first when maintaining the wiki.

```markdown
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
type: source | concept | analysis | entity
created: YYYY-MM-DD
updated: YYYY-MM-DD
sources: ["source-filename.md"]
tags: ["tag1", "tag2"]
---
```

One-line summary here.

## Body content

### Related Pages
- [[related-page]] — brief description of relationship
```

## Ingest Workflow
1. Place raw source in `raw/`
2. Create `sources/<slug>.md` with summary
3. Update/create affected `concepts/` and `entities/` pages
4. Update `index.md`, `glossary.md`, `overview.md`
5. Append to `log.md`

## Query Workflow
1. Read `index.md` to find relevant pages
2. Read those pages
3. Synthesize answer with [[citations]]
4. File notable answer as `analyses/<slug>.md` if worth keeping

## Lint Workflow (weekly)
1. Check for broken [[wiki-links]]
2. Find orphan pages (no incoming links)
3. Detect contradictions between pages
4. Check for stale `updated:` dates
5. Update `index.md` completeness
```

### 1.3 Initialize Core Pages

**`wiki/index.md`** — The master catalog:

```markdown
# Wiki Index

Last linted: 2026-05-01

## Sources
| Page | Summary | Tags |
|------|---------|------|
| [[sources/llm-wiki-karpathy]] | Karpathy's compounding knowledge pattern | #llm #memory #pattern |

## Concepts
| Page | Summary |
|------|---------|
| [[concepts/compounding-knowledge]] | Knowledge that builds on itself vs. stateless retrieval |

## Analyses
| Page | Summary | Date |
|------|---------|------|
| [[analyses/kb-landscape-2026-04]] | Research on AI agent knowledge bases | 2026-04-30 |

## Entities
| Page | Type |
|------|------|
```

**`wiki/log.md`** — Append-only:

```markdown
# Wiki Log

## [2026-05-01] init | Wiki structure created
Created SCHEMA.md, index.md, log.md, overview.md, glossary.md.
Sources, concepts, analyses, entities directories initialized.
```

**`wiki/glossary.md`** — Living terminology:

```markdown
# Glossary

## Compounding Knowledge
*Canonical term.* Knowledge accumulated and cross-referenced such that each
new addition strengthens the whole. Contrast with stateless retrieval.

*See also:* [[concepts/compounding-knowledge]], [[sources/llm-wiki-karpathy]]
```

### 1.4 Convert Existing Memory Files

Your current `memory/YYYY-MM-DD.md` and `MEMORY.md` are close — add frontmatter:

```markdown
---
title: "Memory: 2026-04-30"
type: memory
created: 2026-04-30
updated: 2026-04-30
tags: ["research", "ai-agents", "knowledge-bases"]
sources: []
---

# 2026-04-30

...existing content...
```

Also create `memory/index.md`:

```markdown
---
title: "Memory Index"
type: index
created: 2026-05-01
updated: 2026-05-01
---

# Memory Index

| Date | Tags | Key Events |
|------|------|------------|
| [[2026-04-30]] | #research #ai-agents | KB research project initiated |
```

---

## Phase 2: Search Layer — Hybrid BM25 + Vector (Days 3–5)

### 2.1 Install `qmd` (Recommended)

`qmd` is the tool Karpathy's community built — hybrid BM25 + vector + LLM re-ranking.

```bash
# Check if available
which qmd || pip install qmd

# If not on PyPI, check community repos:
# https://github.com/gowtham0992/llm-wiki-link (has API + search)
```

**Alternative: Roll your own with `ripgrep` + `sqlite-vec`:**

```bash
# Install ripgrep (if not present)
sudo apt-get install ripgrep

# Install sqlite-vec (Python)
pip install sqlite-vec model2vec
```

### 2.2 Create Search Script (`tools/search-vault.py`)

```python
#!/usr/bin/env python3
"""Hybrid search over the markdown vault."""

import sqlite_vec
import sqlite3
import json
import os
import re
from pathlib import Path
from model2vec import StaticModel

VAULT_PATH = Path.home() / ".openclaw/workspace"
DB_PATH = VAULT_PATH / ".vault-search.db"

# Load lightweight embedding model
model = StaticModel.from_pretrained("minishlab/potion-base-8M")

def init_db():
    db = sqlite3.connect(DB_PATH)
    db.enable_load_extension(True)
    sqlite_vec.load(db)
    db.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS docs USING vec0(
            path TEXT PRIMARY KEY,
            embedding FLOAT[256] distance_metric=cosine
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS contents (
            path TEXT PRIMARY KEY,
            title TEXT,
            body TEXT,
            tags TEXT
        )
    """)
    return db

def index_vault():
    db = init_db()
    for md_file in VAULT_PATH.rglob("*.md"):
        if ".git" in str(md_file):
            continue
        text = md_file.read_text()
        # Extract frontmatter title if present
        title = re.search(r'^title:\s*"?([^"\n]+)"?', text, re.M)
        title = title.group(1) if title else md_file.stem
        # Extract tags
        tags = re.findall(r'#(\w+[-\w+]*)', text)
        # Get embedding of full text
        embedding = model.encode(text)
        db.execute(
            "INSERT OR REPLACE INTO docs VALUES (?, ?)",
            (str(md_file), sqlite_vec.serialize_float32(embedding))
        )
        db.execute(
            "INSERT OR REPLACE INTO contents VALUES (?, ?, ?, ?)",
            (str(md_file), title, text, json.dumps(tags))
        )
    db.commit()
    print(f"Indexed {list(VAULT_PATH.rglob('*.md')).__len__()} documents")

def search(query, k=10):
    db = init_db()
    query_vec = model.encode(query)
    results = db.execute("""
        SELECT docs.path, contents.title, contents.tags, distance
        FROM docs
        JOIN contents ON docs.path = contents.path
        WHERE embedding MATCH ? AND k = ?
        ORDER BY distance
    """, (sqlite_vec.serialize_float32(query_vec), k))
    return results.fetchall()

if __name__ == "__main__":
    import sys
    if sys.argv[1] == "index":
        index_vault()
    elif sys.argv[1] == "search":
        query = " ".join(sys.argv[2:])
        for path, title, tags, dist in search(query):
            print(f"{dist:.3f} | {title} | {Path(path).relative_to(VAULT_PATH)}")
```

### 2.3 Add to `tools/` and Make Executable

```bash
chmod +x tools/search-vault.py
```

Create `tools/reindex.sh`:

```bash
#!/bin/bash
# Reindex the vault — run after significant changes
python3 "$(dirname "$0")/search-vault.py" index
```

---

## Phase 3: Graph Layer — Optional Relational Reasoning (Days 6–10)

Skip this initially. Add when you need multi-hop reasoning or have 500+ pages.

### 3.1 Install Cognee (Recommended for Graph Layer)

```bash
pip install cognee
```

### 3.2 Create Graph Extraction Script (`tools/graph-extract.py`)

```python
#!/usr/bin/env python3
"""Extract knowledge graph from markdown vault using Cognee."""

import cognee
from pathlib import Path

VAULT = Path.home() / ".openclaw/workspace"

def extract_graph():
    # Ingest all markdown files
    for md in VAULT.rglob("*.md"):
        if ".git" in str(md):
            continue
        cognee.add(md.read_text())

    # Cognify: extract entities, relationships, build graph
    cognee.cognify()

    # Now you can query:
    # results = cognee.search("What knowledge bases does Matt use?")

if __name__ == "__main__":
    extract_graph()
```

### 3.3 Alternative: Neo4j Agent Memory (if you want a real graph DB)

```bash
# Docker run Neo4j
docker run -d \
  --name neo4j-agent-memory \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:5

# Install Neo4j Agent Memory extension
# https://github.com/neo4j-labs/agent-memory
```

---

## Phase 4: MCP / Agent Integration (Days 3–7, parallel with Phase 2)

### 4.1 Install an Obsidian MCP Server

Choose one:

**Option A: `obsidian-mcp` (Node-based, 300+ stars)**

```bash
npm install -g obsidian-mcp
# Configure in your MCP settings
```

**Option B: Filesystem-based MCP (simplest, no Obsidian required)**

If you don't want to run Obsidian app, use a filesystem MCP that just reads/writes markdown:

```bash
# Many MCP servers support filesystem operations
# Or use OpenClaw's built-in file tools (read, write, edit)
# which already have full vault access
```

**Option C: Obsidian Local REST API + MCP Bridge**

```bash
# 1. Install obsidian-local-rest-api plugin in Obsidian app
# 2. Configure MCP server to talk to localhost:27124
# 3. Example MCP config (~/.openclaw/mcp-config.json or similar):
```

```json
{
  "mcpServers": {
    "obsidian": {
      "command": "node",
      "args": ["/path/to/obsidian-mcp/dist/index.js"],
      "env": {
        "OBSIDIAN_VAULT": "/home/user/.openclaw/workspace",
        "OBSIDIAN_API_KEY": "your-rest-api-key"
      }
    }
  }
}
```

### 4.2 Create Custom MCP Tools for the Wiki Pattern

Since your wiki follows the Karpathy schema, create specialized tools:

**`tools/mcp-wiki-ingest.py`** — Encapsulates the full ingest workflow:

```python
#!/usr/bin/env python3
"""MCP tool: Ingest a raw source into the wiki."""

import sys
import re
from pathlib import Path
from datetime import datetime

VAULT = Path.home() / ".openclaw/workspace"
RAW_DIR = VAULT / "raw"
WIKI = VAULT / "wiki"

def slugify(text):
    return re.sub(r'[^\w]+', '-', text.lower()).strip('-')

def ingest(source_path: str):
    source = Path(source_path)
    raw_dest = RAW_DIR / source.name
    raw_dest.write_bytes(source.read_bytes())

    # TODO: Call LLM to:
    # 1. Summarize source
    # 2. Create wiki/sources/<slug>.md
    # 3. Update affected concept/entity pages
    # 4. Update index.md, glossary.md, overview.md
    # 5. Append to log.md

    # For now, create stub:
    slug = slugify(source.stem)
    source_page = WIKI / "sources" / f"{slug}.md"
    today = datetime.now().strftime("%Y-%m-%d")

    source_page.write_text(f"""---
title: "{source.stem}"
type: source
created: {today}
updated: {today}
tags: []
sources: ["{raw_dest.name}"]
---

# {source.stem}

*Ingested on {today}. Summary pending LLM processing.*

## Related Pages
- [[index]]
""")

    # Append to log
    log = WIKI / "log.md"
    log_content = log.read_text()
    log.write_text(
        log_content + f"\n## [{today}] ingest | {source.stem}\n"
        f"Created [[sources/{slug}]]. Raw: `{raw_dest.name}`\n"
    )

    print(f"Ingested: {source_page}")

if __name__ == "__main__":
    ingest(sys.argv[1])
```

### 4.3 Register Tools with OpenClaw

Add to your workspace's `TOOLS.md` or `AGENTS.md`:

```markdown
### Wiki Tools

- `python3 tools/search-vault.py search <query>` — Hybrid semantic search
- `python3 tools/search-vault.py index` — Reindex vault
- `python3 tools/mcp-wiki-ingest.py <file>` — Ingest source into wiki
- `python3 tools/graph-extract.py` — Extract knowledge graph (Cognee)
```

---

## Phase 5: Automation — Heartbeat Integration (Day 7+)

### 5.1 Add Wiki Maintenance to Heartbeat

Update `HEARTBEAT.md`:

```markdown
# Heartbeat Tasks

## Wiki Maintenance (run every 6 hours)
- [ ] Check for new files in `raw/` — if found, run ingest workflow
- [ ] Review `wiki/log.md` for pending items
- [ ] Run `tools/search-vault.py index` if files changed
- [ ] Weekly lint: check broken links, orphans, stale pages
```

### 5.2 Cron Job for Weekly Lint

```bash
# Add via cron tool or crontab
crontab -e
# Add: 0 9 * * 1 cd ~/.openclaw/workspace && python3 tools/wiki-lint.py
```

Create `tools/wiki-lint.py`:

```python
#!/usr/bin/env python3
"""Weekly wiki health check."""

from pathlib import Path
import re

VAULT = Path.home() / ".openclaw/workspace/wiki"

def find_broken_links():
    all_pages = set(p.stem for p in VAULT.rglob("*.md"))
    broken = []
    for page in VAULT.rglob("*.md"):
        text = page.read_text()
        for link in re.findall(r'\[\[([^\]]+)\]\]', text):
            slug = link.split('/')[0] if '/' in link else link
            if slug not in all_pages:
                broken.append((page, link))
    return broken

def find_orphans():
    all_links = set()
    for page in VAULT.rglob("*.md"):
        text = page.read_text()
        for link in re.findall(r'\[\[([^\]]+)\]\]', text):
            all_links.add(link.split('/')[0] if '/' in link else link)

    orphans = []
    for page in VAULT.rglob("*.md"):
        if page.stem not in all_links and page.name not in ["index.md", "log.md", "overview.md", "glossary.md", "SCHEMA.md"]:
            orphans.append(page)
    return orphans

if __name__ == "__main__":
    broken = find_broken_links()
    orphans = find_orphans()

    print(f"Broken links: {len(broken)}")
    for page, link in broken:
        print(f"  {page.relative_to(VAULT)} -> [[{link}]]")

    print(f"\nOrphan pages: {len(orphans)}")
    for page in orphans:
        print(f"  {page.relative_to(VAULT)}")
```

---

## Quick-Start Checklist

| Step | Command / Action | Time |
|------|-----------------|------|
| 1. Create wiki directories | `mkdir -p wiki/{sources,concepts,analyses,entities}` | 1 min |
| 2. Write SCHEMA.md | Copy from Phase 1.2 | 10 min |
| 3. Create core pages | index.md, log.md, overview.md, glossary.md | 15 min |
| 4. Add frontmatter to memory files | Update existing memory/YYYY-MM-DD.md | 20 min |
| 5. Install search dependencies | `pip install sqlite-vec model2vec` | 5 min |
| 6. Create search script | Copy `tools/search-vault.py` | 10 min |
| 7. Index the vault | `python3 tools/search-vault.py index` | 2 min |
| 8. Test search | `python3 tools/search-vault.py search "knowledge base"` | 1 min |
| 9. Create ingest script | Copy `tools/mcp-wiki-ingest.py` | 10 min |
| 10. Register tools in TOOLS.md | Document available commands | 5 min |
| 11. Set up weekly lint cron | `crontab -e` + `tools/wiki-lint.py` | 5 min |

**Total setup time: ~90 minutes**

---

## Migration Strategy for Existing Workspace

Your workspace already has:
- `memory/` — Daily notes
- `MEMORY.md` — Curated long-term memory
- `AGENTS.md`, `SOUL.md`, `USER.md`, `TOOLS.md` — Structured context files

### Minimal Migration Path:

1. **Keep existing files as-is** — they're already structured knowledge
2. **Add `memory/index.md`** — Catalog of daily notes with wikilinks
3. **Create `wiki/`** alongside — New compounding knowledge goes here; keep `memory/` for raw daily logs
4. **Cross-link** — Reference `memory/2026-04-30` from `wiki/analyses/` pages
5. **Unified search** — Index both `memory/` and `wiki/` in the same sqlite-vec DB

This gives you:
- `memory/` = raw, chronological, agent-readable (existing)
- `wiki/` = compiled, cross-referenced, compounding (new)
- Both searchable via the same hybrid index

---

## Scaling Triggers

| Condition | Action |
|-----------|--------|
| Vault < 100 pages | `index.md` + ripgrep is sufficient |
| Vault 100–500 pages | Add sqlite-vec search |
| Vault 500+ pages | Add Cognee graph extraction |
| Multi-agent access needed | Set up MCP server |
| Need temporal reasoning ("what did I know in March?") | Evaluate Zep/Graphiti |
| Production agent deployment | Evaluate Mem0g or Letta as memory backend |

---

## Summary

The Convergence system is intentionally **progressive** — start with plain markdown + frontmatter + wikilinks, add search when you need it, add graph extraction when you outgrow simple linking. At every stage, your knowledge remains human-readable, git-trackable, and portable.

The key principle from Karpathy: **the LLM maintains the wiki, you maintain the sources and the questions.**

---

*Guide written by Claw 🐾 | For Matt's OpenClaw workspace*
