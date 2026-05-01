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


def today():
    return datetime.now().strftime("%Y-%m-%d")


def ingest(source_path: str):
    source = Path(source_path)
    if not source.exists():
        print(f"Error: file not found: {source}")
        sys.exit(1)

    # Ensure raw directory exists
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    # Copy to raw/
    raw_dest = RAW_DIR / source.name
    raw_dest.write_bytes(source.read_bytes())

    slug = slugify(source.stem)
    t = today()

    # Create source page
    source_page = WIKI / "sources" / f"{slug}.md"
    source_page.parent.mkdir(parents=True, exist_ok=True)

    source_page.write_text(f"""---
title: "{source.stem}"
type: source
created: {t}
updated: {t}
tags: []
sources: ["{raw_dest.name}"]
---

# {source.stem}

*Ingested on {t}. Summary pending LLM processing.*

## Related Pages
- [[index]]
""")

    # Append to log
    log = WIKI / "log.md"
    if log.exists():
        log_content = log.read_text()
    else:
        log_content = "# Wiki Log\n\n"

    log.write_text(
        log_content + f"\n## [{t}] ingest | {source.stem}\n"
        f"Created [[sources/{slug}]]. Raw: `{raw_dest.name}`\n"
    )

    print(f"Ingested: {source_page}")
    print(f"Raw: {raw_dest}")
    print(f"Log updated: {log}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: mcp-wiki-ingest.py <file>")
        sys.exit(1)
    ingest(sys.argv[1])
