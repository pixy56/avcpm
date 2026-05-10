# HEARTBEAT.md

## Wiki Maintenance (run every 6 hours via cron)
- [x] **Cron:** `raw-check-ingest` — Check for new files in `raw/` — if found, run ingest workflow
- [x] **Cron:** `wiki-log-review` — Review `wiki/log.md` for pending items
- [x] **Cron:** `wiki-weekly-lint` — Weekly lint: broken links, orphans, stale pages
- [x] **MEMORY.md created** — Curated long-term memory backbone
- [ ] Search index reindex — Run when files change (TBD if needed)

## Regular Checks
- [ ] Email inbox
- [ ] Calendar events
- [ ] Weather

## Keep this file empty (or with only comments) to skip heartbeat API calls.

# Add tasks below when you want the agent to check something periodically.

