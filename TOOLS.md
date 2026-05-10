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

### LLM Backend (Ollama)

- **Ollama host:** `http://localhost:11434`
- **Models available:** qwen3.6:35b (36B, slow but free), gemma4:31b, gemma4:latest (8B)
- **Keep-alive:** `GRAPHIFY_OLLAMA_KEEP_ALIVE=30m` — keeps model loaded 30 min after last use
  - Set in `~/.bashrc` (already done)
  - Options: `30m`, `2h`, `-1` (permanent, max power draw)
  - Current: 30 minutes (covers daily 4 AM extraction window)
- **Context window:** Auto-calculated per prompt (env override: `GRAPHIFY_OLLAMA_NUM_CTX`)
- **Timeout:** 600s default (override: `GRAPHIFY_API_TIMEOUT`)
- **Trade-off:** Loaded 35B model = +200-400W GPU power draw. Unloaded = cold start takes 30-60s to load from disk.

### TTS

- Preferred voice: "Nova" (warm, slightly British)
- Default speaker: Kitchen HomePod
```

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

---

Add whatever helps you do your job. This is your cheat sheet.
