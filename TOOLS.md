# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to your setup.

## What Goes Here

Things like:

- Camera names and locations
- SSH hosts and aliases
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

## Examples

```markdown
## Knowledge Base Tools

- `~/.openclaw/tools-venv/bin/python3 tools/search-vault.py search <query>` — Hybrid semantic search
- `~/.openclaw/tools-venv/bin/python3 tools/search-vault.py grep <keyword>` — Keyword search
- `~/.openclaw/tools-venv/bin/python3 tools/search-vault.py index` — Reindex vault
- `python3 tools/mcp-wiki-ingest.py <file>` — Ingest source into wiki
- `python3 tools/wiki-lint.py` — Check for broken links, orphans, stale pages
- `python3 tools/mcp-server.py` — MCP server for external agent access (stdio)

### MCP Configuration
- Config: `~/.openclaw/mcp-config.json`
- Server: `openclaw-wiki` — tools: wiki_search, wiki_read, wiki_write, wiki_ingest, wiki_lint, wiki_index, wiki_log_append

### Obsidian Sync
- Vault path: `~/.openclaw/workspace`
- Open Obsidian → "Open folder as vault" → select workspace directory
- All wiki, memory, and research files are immediately browsable
- See `wiki/OBSIDIAN_SETUP.md` for detailed setup and recommended plugins

### Cameras

- living-room → Main area, 180° wide angle
- front-door → Entrance, motion-triggered

### SSH

- home-server → 192.168.1.100, user: admin

### TTS

- Preferred voice: "Nova" (warm, slightly British)
- Default speaker: Kitchen HomePod
```

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

---

Add whatever helps you do your job. This is your cheat sheet.
