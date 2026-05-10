# MEMORY.md - Curated Long-Term Memory

## Philosophy

MEMORY.md is the **distilled essence** — not raw logs. Daily notes go in `memory/YYYY-MM-DD.md`; curated wisdom goes here.

## Project: Graphify + LLM Wiki Integration

**Status:** Active — Phases 1 & 2 complete, Phase 3 in progress.
**Decision:** Use both Graphify (auto-indexer) and LLM Wiki (auto-author) together.
**Rationale:** Graphify provides machine-readable structure; LLM Wiki provides human-readable narrative. They are complementary, not competitive.

## Setup Details

- **Graphify:** Installed in `~/.openclaw/graphify-venv`
- **Backend:** Ollama (qwen3.6:35b) for semantic extraction
- **Daily cron:** `graphify-daily-update` at 4:00 AM CDT (AST-only)
- **Wiki cron:** `raw-check-ingest` + `wiki-log-review` every 6 hours
- **MCP:** `graphify` server registered in `~/.openclaw/mcp-config.json`
- **Schema:** `WIKI.md` defines wiki structure and workflows

## Lessons Learned

- **Subagent timeouts happen.** The wiki ingest subagent hit a 2-minute timeout at 16 tool calls. Large ingest tasks should either run longer or be done in the main session.
- **Ollama works but is slow.** Semantic extraction with qwen3.6:35b is functional but takes minutes. For production use, a cloud LLM (Gemini, Claude) would be faster.
- **Graphify's AST extraction is fast.** The `graphify update .` command runs in seconds and costs nothing.

## Open Questions

- Should we set up a cloud LLM API key for faster semantic extraction?
- How often should the full `graphify extract .` (with LLM) run vs. `graphify update .` (AST-only)?
- Should we export an Obsidian vault for browsing?

## Preferences

- **Matt** prefers direct, factual communication.
- **Timezone:** America/Chicago.
- **Model:** ollama/kimi-k2.6:cloud for general chat.
