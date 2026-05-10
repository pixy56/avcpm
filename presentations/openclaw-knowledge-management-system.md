# OpenClaw Knowledge Management System

**Presenter:** Matt  
**Date:** 2026-05-09  
**System:** OpenClaw + Graphify + LLM Wiki + Self-Improving Agent

---

## Slide 1: Executive Summary

**What We Built:** A fully automated, AI-powered personal knowledge management system that turns your workspace into a living, queryable, self-improving knowledge base.

**Core Philosophy:**
- Human curates what goes in
- LLM does all maintenance
- Knowledge compounds over time
- System learns from its own mistakes

---

## Slide 2: Feature List

### Knowledge Capture
- ✅ **Raw Sources** — Drop articles, PDFs, transcripts, code into `raw/`
- ✅ **Auto-Ingest** — AI reads, summarizes, and files sources every 6 hours
- ✅ **GitHub Integration** — Pull code repos for analysis and review
- ✅ **Multi-Engine Search** — `web_search` for discovery, `web_fetch` for deep dives

### Knowledge Organization
- ✅ **Graphify Knowledge Graph** — Auto-extracts entities, relationships, clusters from all files
  - 2,251 nodes, 3,366 edges, 209 communities
  - 71.5× token reduction vs naive file-reading
- ✅ **LLM Wiki** — Markdown articles with `[[wikilinks]]` and YAML frontmatter
  - Sources, Concepts, Entities, Comparisons
- ✅ **Memory System** — Daily logs + curated long-term `MEMORY.md`
- ✅ **Structured Learnings** — `.learnings/` directory for errors, insights, best practices

### Knowledge Retrieval
- ✅ **Semantic Search** — sqlite-vec + model2vec hybrid search (78 docs indexed)
- ✅ **Graph Queries** — BFS/DFS traversal of knowledge graph
- ✅ **Wiki Index** — Master index linking all pages
- ✅ **MCP Server** — Native `graph_query` tool for agents
- ✅ **Obsidian Dashboard** — Dataview-powered learning dashboard

### Automation
- ✅ **Daily Graph Updates** — `graphify update .` at 4:00 AM (AST-only, no API cost)
- ✅ **6-Hour Wiki Ingest** — Checks `raw/` for new sources
- ✅ **6-Hour Log Review** — Follows up on pending items
- ✅ **Weekly Lint** — Broken links, orphans, stale pages
- ✅ **Heartbeat Checks** — Periodic system maintenance + `.learnings/` review

### Agent Team Coordination
- ✅ **Multi-Agent Reviews** — 4 specialized agents (Architecture, Security, Performance, Testing)
- ✅ **Unified Reports** — Compiled into single prioritized report
- ✅ **Wiki Integration** — Reports auto-ingested into knowledge base
- ✅ **Shared Learnings** — AGENTS.md "Multi-Agent Learnings" section inherited by all agents

---

## Slide 3: Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        OPENCLAW WORKSPACE                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐     │
│  │   Raw Input  │───▶│   Ingest     │───▶│   LLM Wiki   │     │
│  │   (raw/)     │    │   Pipeline   │    │   (wiki/)    │     │
│  │              │    │              │    │              │     │
│  │ • Articles   │    │ AI reads     │    │ • Sources    │     │
│  │ • PDFs       │    │ • Summarizes │    │ • Concepts   │     │
│  │ • Code       │    │ • Cross-ref  │    │ • Entities   │     │
│  │ • Media      │    │ • Updates    │    │ • Compare    │     │
│  └──────────────┘    │   index      │    └──────────────┘     │
│                      └──────────────┘           ▲             │
│                                                   │             │
│  ┌───────────────────────────────────────────────┐│             │
│  │              GRAPHIFY KNOWLEDGE GRAPH           ││             │
│  │                                                ││             │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐   ││             │
│  │  │  Detect  │─▶│ Extract  │─▶│  Build   │   ││             │
│  │  │ (scan)   │  │ (AST+LLM)│  │  Graph   │   ││             │
│  │  └──────────┘  └──────────┘  └────┬─────┘   ││             │
│  │                                   ▼          ││             │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐   ││             │
│  │  │ Cluster  │─▶│ Analyze  │─▶│  Report  │   ││             │
│  │  │(Leiden)  │  │(god nodes│  │(GRAPH_   │   ││             │
│  │  └──────────┘  │surprises)│  │ REPORT)  │   ││             │
│  │                └──────────┘  └──────────┘   ││             │
│  └───────────────────────────────────────────────┘│             │
│                      │                            │             │
│                      ▼                            │             │
│  ┌────────────────────────────────────────────────┴────────┐  │
│  │                     MCP SERVER                           │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐             │  │
│  │  │  graph_  │  │  graph_  │  │  graph_  │             │  │
│  │  │  query   │  │  path    │  │ explain  │             │  │
│  │  └──────────┘  └──────────┘  └──────────┘             │  │
│  └─────────────────────────────────────────────────────────┘  │
│                      │                                         │
│                      ▼                                         │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │                    AGENT INTERFACE                       │  │
│  │                                                        │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐  │  │
│  │  │  Search  │  │  Query   │  │  Multi-Agent Review  │  │  │
│  │  │  (vec)   │  │  (graph) │  │  (arch/sec/perf/test)│  │  │
│  │  └──────────┘  └──────────┘  └──────────────────────┘  │  │
│  └─────────────────────────────────────────────────────────┘  │
│                      │                                         │
│                      ▼                                         │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │                  SELF-IMPROVING LAYER                  │  │
│  │                                                        │  │
│  │  ┌──────────────┐      ┌──────────────┐              │  │
│  │  │ .learnings/  │─────▶│  Review +    │              │  │
│  │  │ ERRORS.md    │      │  Promote     │              │  │
│  │  │ LEARNINGS.md │─────▶│  to:         │              │  │
│  │  │ FEATURES.md  │      │  AGENTS.md   │              │  │
│  │  └──────────────┘      │  MEMORY.md   │              │  │
│  │                        │  TOOLS.md    │              │  │
│  │                        └──────────────┘              │  │
│  └─────────────────────────────────────────────────────────┘  │
│                      │                                         │
│                      ▼                                         │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │                  MEMORY SYSTEM                           │  │
│  │                                                        │  │
│  │  ┌──────────────┐      ┌──────────────┐              │  │
│  │  │ Daily Logs   │      │  Curated     │              │  │
│  │  │ (memory/*.md)│─────▶│  MEMORY.md   │              │  │
│  │  └──────────────┘      └──────────────┘              │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │                  AUTOMATION LAYER                        │  │
│  │                                                        │  │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐        │  │
│  │  │ Daily      │ │ 6-Hour     │ │ 6-Hour     │        │  │
│  │  │ Graphify   │ │ Wiki       │ │ Log        │        │  │
│  │  │ Update     │ │ Ingest     │ │ Review     │        │  │
│  │  │ (4 AM)     │ │ (6-hourly) │ │ (6-hourly) │        │  │
│  │  └────────────┘ └────────────┘ └────────────┘        │  │
│  │  ┌────────────────────────────────────────────┐        │  │
│  │  │ Weekly Lint (Monday 5 AM)                   │        │  │
│  │  └────────────────────────────────────────────┘        │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Slide 4: Data Flow Diagram

```
USER / EXTERNAL
      │
      │ 1. Drop source in raw/
      │ 2. GitHub repo synced
      │ 3. Ask question
      ▼
┌─────────────────┐
│   RAW INPUTS    │
│                 │
│ • raw/*.md      │
│ • raw/*.pdf     │
│ • Code repos    │
│ • Session notes │
│ • Search results│
└────────┬────────┘
         │
         ├────────────────────────┐
         │                        │
         ▼                        ▼
┌─────────────────┐    ┌─────────────────┐
│  GRAPHIFY       │    │  LLM WIKI       │
│  (Auto-Indexer) │    │  (Auto-Author)  │
│                 │    │                 │
│ • AST parse     │    │ • Read source   │
│ • Extract       │    │ • Summarize     │
│   entities      │    │ • Cross-ref     │
│ • Build graph   │    │ • Write pages   │
│ • Detect        │    │ • Update index  │
│   communities   │    │ • Update log    │
└────────┬────────┘    └────────┬────────┘
         │                        │
         │     ┌──────────────────┘
         │     │
         ▼     ▼
┌─────────────────┐
│  KNOWLEDGE BASE │
│                 │
│ • graph.json    │  ← Machine-readable
│ • wiki/*.md     │  ← Human-readable
│ • .learnings/   │  ← Self-improving
│ • index.md      │  ← Navigation
│ • MEMORY.md     │  ← Long-term memory
└────────┬────────┘
         │
         ├────────────────────────┐
         │                        │
         ▼                        ▼
┌─────────────────┐    ┌─────────────────┐
│  QUERY METHODS  │    │  SEARCH METHODS │
│                 │    │                 │
│ • graph_query   │    │ • Semantic      │
│ • graph_path    │    │   (sqlite-vec)  │
│ • graph_explain │    │ • Keyword       │
│ • BFS/DFS       │    │   (grep)        │
└────────┬────────┘    └────────┬────────┘
         │                        │
         └──────────┬─────────────┘
                    │
                    ▼
         ┌─────────────────┐
         │  AGENT ANSWERS  │
         │                 │
         │ • Synthesized   │
         │   with citations│
         │ • New knowledge │
         │   filed back    │
         │ • Actions taken │
         │   automatically │
         └─────────────────┘
```

---

## Slide 5: Component Deep Dive — Graphify

### What It Is
An open-source AI coding-assistant skill that converts any folder into a **queryable knowledge graph**.

### 7-Stage Pipeline

```
1. DETECT      → Scan directory, filter by extension, respect .graphifyignore
2. EXTRACT     → Three-pass extraction:
                   Pass 1: AST parsing (29 languages) — deterministic, zero LLM cost
                   Pass 2: Whisper transcription (audio/video)
                   Pass 3: LLM subagents (docs, PDFs, images)
3. BUILD GRAPH → NetworkX graph with confidence tags:
                   EXTRACTED (1.0) — explicit in source
                   INFERRED (0.0-1.0) — reasonable inference
                   AMBIGUOUS — flag for review
4. CLUSTER     → Leiden community detection (no embeddings, no vector DB)
5. ANALYZE     → Identify "god nodes" (highest-degree hubs), surprising connections
6. REPORT      → Generate GRAPH_REPORT.md (plain-language summary)
7. EXPORT      → Interactive HTML, Obsidian vault, MCP server, Neo4j
```

### Key Metrics (This Workspace)
- **2,251 nodes** — entities, functions, files, concepts
- **3,366 edges** — relationships, calls, references
- **209 communities** — clustered knowledge domains
- **86% EXTRACTED** — high-confidence edges
- **71.5× token reduction** — vs reading raw files

---

## Slide 6: Component Deep Dive — LLM Wiki

### What It Is
A knowledge management pattern originated by Andrej Karpathy. Instead of RAG (retrieving chunks every query), an LLM incrementally compiles sources into a **persistent, interlinked markdown wiki**.

### Three-Layer Architecture

```
┌─────────────────────────────────────┐
│  LAYER 3: SCHEMA (AGENTS.md/WIKI.md)│
│  Configuration & conventions        │
│  • Folder structure                 │
│  • Page templates                   │
│  • Ingest/query/lint workflows      │
└─────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────┐
│  LAYER 2: THE WIKI (wiki/)          │
│  LLM-generated knowledge            │
│                                     │
│  • wiki/index.md — Master index     │
│  • wiki/log.md — Changelog          │
│  • wiki/sources/ — Source summaries │
│  • wiki/concepts/ — Abstract ideas  │
│  • wiki/entities/ — People/tools  │
│  • wiki/comparisons/ — Side-by-side │
│  • wiki/Learning-Dashboard.md       │
└─────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────┐
│  LAYER 1: RAW SOURCES (raw/)        │
│  Immutable input                    │
│  • Articles, PDFs, transcripts        │
│  • Code repositories                │
│  • Research documents               │
│  • Search results                   │
└─────────────────────────────────────┘
```

### Core Operations
1. **Ingest** — AI reads source → writes summary → cascades updates → updates index + log
2. **Query** — AI reads index → finds relevant pages → synthesizes answer with citations
3. **Lint** — Health check for contradictions, orphans, stale claims, broken links

### Page Template (Every Wiki Page)
```yaml
---
title: "Page Title"
type: concept | entity | source | comparison
created: YYYY-MM-DD
updated: YYYY-MM-DD
tags: []
status: draft | stable | archived
source_refs: []
related:
  - [[Linked Page]]
---
```

---

## Slide 7: Component Deep Dive — Self-Improving Agent

### What It Is
A skill that logs errors and learnings to structured markdown, then promotes broadly applicable insights to project memory.

### The Learning Loop

```
┌─────────────────┐
│   Experience    │
│  (error/insight)│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   LOG           │
│  .learnings/    │
│                 │
│ • ERRORS.md     │
│ • LEARNINGS.md  │
│ • FEATURES.md   │
│ • CRON_LOG.md   │
│ • PERFORMANCE.md│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   REVIEW        │
│  (weekly cron)  │
│                 │
│ • Same error    │
│   >2x?         │
│ • Pattern       │
│   validated?    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   PROMOTE       │
│                 │
│ • SOUL.md       │ ← Behavioral
│ • AGENTS.md     │ ← Workflows
│ • TOOLS.md      │ ← Tool gotchas
│ • MEMORY.md     │ ← Knowledge
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   IMPROVE       │
│  Next session   │
│  inherits       │
│  learnings      │
└─────────────────┘
```

### Current `.learnings/` Population

| File | Entries | Status |
|------|---------|--------|
| `ERRORS.md` | 9 errors | 5 resolved, 4 pending |
| `LEARNINGS.md` | 0 (ready for input) | — |
| `FEATURE_REQUESTS.md` | 0 (ready for input) | — |
| `CRON_LOG.md` | 0 (ready for input) | — |
| `PERFORMANCE.md` | 7 baselines | Tracked |

### Sample Error Entry
```markdown
## [ERR-20260509-001] Subagent timeout at 16 tool calls
**Priority:** high | **Status:** resolved | **Area:** tool
**Summary:** Wiki ingest subagent timed out after 16 tool calls / 2 minutes
**Details:** Large codebase review exceeded subagent budget
**Suggested Fix:** Ingest >10 files → main session, not subagent
**Recovery:** Retry in main session; consider splitting into smaller tasks
```

---

## Slide 8: Component Deep Dive — LLM Backend (Ollama)

### What It Is
Local LLM inference server running multiple models for different tasks.

### Model Zoo (Current)

| Model | Size | Role | Speed | Notes |
|-------|------|------|-------|-------|
| **qwen3.6:35b** | 36B | Semantic extraction (Graphify) | 🟡 Slow (3-4 min) | Primary backend for doc/image analysis |
| **gemma4:31b** | 31B | General chat fallback | 🟡 Medium | Alternative when qwen is busy |
| **gemma4:latest** | 8B | Fast tasks | 🟢 Fast | Lightweight, low latency |
| **kimi-k2.6:cloud** | — | General chat (default) | 🟢 Fast | Cloud-backed, always available |
| **kimi-k2.5:cloud** | — | Backup chat | 🟢 Fast | Fallback model |
| **glm-5.1:cloud** | — | Code tasks | 🟢 Fast | General purpose |
| **minimax-m2.7:cloud** | — | Creative tasks | 🟢 Fast | Diverse capabilities |

### Performance Characteristics

| Task | Model | Typical Time | Cost |
|------|-------|-------------|------|
| Graphify AST update (no LLM) | — | ~5s | FREE |
| Graphify semantic extract | qwen3.6:35b | 180-240s | FREE (local GPU) |
| General chat | kimi-k2.6:cloud | ~2s | FREE (cloud) |
| Code review (subagent) | kimi-k2.6:cloud | 60-120s | FREE (cloud) |
| Wiki ingest (subagent) | kimi-k2.6:cloud | ~120s | FREE (cloud) |
| Search index rebuild | model2vec | ~10s | FREE |

### Trade-offs

| Approach | Pros | Cons |
|----------|------|------|
| **Ollama local (qwen3.6:35b)** | Free, private, no API keys | Slow (3-4 min per extraction), GPU-bound |
| **Cloud models (kimi-k2.6)** | Fast, reliable, no hardware | Requires internet, provider-dependent |
| **Hybrid (current)** | Best of both: AST is free/fast, semantic uses cloud when needed | Complexity of two backends |

### Open Question
**Should we add a cloud LLM API key (Gemini/Claude/OpenAI) for faster semantic extraction?**
- Current: qwen3.6:35b is functional but 3-4 minutes per semantic extraction
- Cloud option: Gemini 3 Flash, Claude 3.5 Sonnet, GPT-4.1 Mini — 10-30 seconds
- Cost: ~$0.50-3.00 per 1M tokens (semantic extraction is ~10-50K tokens)

---

## Slide 9: Component Deep Dive — Backup System

### What It Is
A comprehensive backup strategy covering configuration, knowledge, and automation.

### Backup Location
```
~/.openclaw/backups/20260509-200201/
```

### What's Backed Up (68 files, 2.4 MB)

| Component | Files | Notes |
|-----------|-------|-------|
| **Config** | 5 | openclaw.json, mcp-config.json, exec-approvals, update-check |
| **Cron jobs** | 4 | graphify daily, wiki ingest 6h, log review 6h, weekly lint |
| **Identity** | — | Agent identity files |
| **Credentials** | — | API keys, tokens (encrypted) |
| **Workspace config** | 6 | AGENTS.md, SOUL.md, USER.md, MEMORY.md, WIKI.md, HEARTBEAT.md |
| **Memory** | — | Daily session logs (memory/YYYY-MM-DD.md) |
| **Wiki** | 16+ | All wiki pages (sources, concepts, entities, comparisons) |
| **Raw sources** | — | Source inputs |
| **Graphify** | 2 | GRAPH_REPORT.md, graph.json |
| **Logs** | — | Session logs |

### What's NOT Backed Up (by design)

| Component | Why Excluded | Recovery |
|-----------|-------------|----------|
| `graphify-out/cache/` | Large AST cache, rebuildable | `graphify update .` (5s) |
| `.git/` | Git history on GitHub | `git clone` |
| `tools-venv/` | Python venv, reinstallable | `pip install -r requirements.txt` |
| `graphify-venv/` | Graphify venv, reinstallable | `pip install graphifyy` |

### GitHub as Secondary Backup
- Repository: https://github.com/pixy56/avcpm.git
- All wiki infrastructure, reports, and config version-controlled
- `git push` after significant changes

### Restore Process
```bash
# 1. Stop OpenClaw gateway
# 2. Copy backup files back to ~/.openclaw/
cp -r ~/.openclaw/backups/20260509-200201/* ~/.openclaw/
# 3. Restore git repo (if needed)
git clone https://github.com/pixy56/avcpm.git ~/.openclaw/workspace
# 4. Reinstall Python environments
python3 -m venv ~/.openclaw/tools-venv
python3 -m venv ~/.openclaw/graphify-venv
# 5. Restart gateway
# 6. Verify: openclaw cron list
```

---

## Slide 10: Component Deep Dive — Automation Layer

### Cron Jobs (4 Active in OpenClaw Scheduler)

```
┌────────────────────────────────────────┐
│  graphify-daily-update                 │
│  Schedule: 0 4 * * * (4:00 AM CDT)     │
│  Action: graphify update .              │
│  Cost: FREE (AST-only, no LLM calls)   │
│  Purpose: Keep code graph current        │
└────────────────────────────────────────┘

┌────────────────────────────────────────┐
│  raw-check-ingest                      │
│  Schedule: 0 */6 * * * (every 6 hours)  │
│  Action: Scan raw/ → ingest to wiki     │
│  Purpose: Auto-process new sources      │
└────────────────────────────────────────┘

┌────────────────────────────────────────┐
│  wiki-log-review                       │
│  Schedule: 0 */6 * * * (every 6 hours)  │
│  Action: Check log.md for pending items │
│  Purpose: Follow up on TODOs           │
└────────────────────────────────────────┘

┌────────────────────────────────────────┐
│  wiki-weekly-lint                      │
│  Schedule: 0 5 * * 1 (Monday 5 AM)     │
│  Action: Broken links, orphans, stale   │
│  Purpose: Wiki health check            │
└────────────────────────────────────────┘
```

### Trigger Flow
```
New source in raw/
       │
       ▼
┌──────────────┐
│ Heartbeat    │◄──── Checks every ~30 min
│ or Cron      │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Ingest Agent │
│ (kimi-k2.6)  │
└──────┬───────┘
       │
       ├───────▶ Create source page
       ├───────▶ Create/update concepts
       ├───────▶ Create/update entities
       ├───────▶ Update index.md
       └───────▶ Append to log.md
```

---

## Slide 11: Component Deep Dive — Multi-Agent Review System

### Review Team Structure

```
┌─────────────────────────────────────────┐
│           ORCHESTRATOR (You / Main)       │
│           Coordinates, delegates           │
└──────────────┬────────────────────────────┘
               │
       ┌───────┼───────┐
       │       │       │
       ▼       ▼       ▼          ▼
┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
│ARCHITECT│ │SECURITY │ │PERFORMANCE│ │TESTING │
│Reviewer  │ │Reviewer │ │Reviewer  │ │Reviewer │
│(kimi)   │ │(kimi)   │ │(kimi)    │ │(kimi)   │
└────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘
     │           │           │           │
     └───────────┴─────┬─────┴───────────┘
                       │
                       ▼
            ┌─────────────────────┐
            │  UNIFIED REPORT     │
            │  • Priority matrix  │
            │  • Cross-cutting    │
            │    findings         │
            │  • Action items     │
            └──────────┬──────────┘
                       │
                       ▼
            ┌─────────────────────┐
            │  WIKI INGEST        │
            │  • Source page      │
            │  • Concept pages    │
            │  • Entity pages     │
            │  • Log entry        │
            └─────────────────────┘
```

### Shared Agent Context (AGENTS.md)
All future agents inherit known anti-patterns at startup:
- **Architecture:** `sys.exit()` in libs, CLI/lib conflation, non-unique IDs, tight coupling
- **Security:** Path traversal, plaintext approval, symlink-following, TOCTOU races
- **Performance:** No file locking, monolithic JSON, no LRU cache, O(n²) traversals
- **Testing:** Untested auth, security, ledger integrity, mixed frameworks

### Orchestrator Rules
- Ingest >10 files → main session (subagent timeout at 16 tools)
- Large repos (>10k lines) → split into 4+ focused subagents
- Repos with auth/security → boost Security agent to 24 tools
- Repos with 0 tests → skip Testing agent, redirect budget to Security

### AVCPM Review Results

| Reviewer | Runtime | Tokens | Key Finding |
|----------|---------|--------|-------------|
| Architecture | 1m21s | 221K | CLI/library conflation, non-unique commit IDs |
| Security | 4m2s | 110K | **3 Critical** path traversal vulnerabilities |
| Performance | 1m56s | 352K | No caching, no file locking, O(n²) operations |
| Testing | 2m2s | 385K | 5 modules untested, mixed frameworks |

---

## Slide 12: Integration Points

### How Components Connect

```
┌─────────────────────────────────────────────────────────────┐
│  EXTERNAL INPUTS                                            │
│  • User messages  • GitHub repos  • Raw files  • Web pages  │
└──────────────────────────┬────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  OPENCLAW GATEWAY                                           │
│  • Routes messages to sessions                              │
│  • Manages models (kimi-k2.6, ollama, etc.)                 │
│  • Handles heartbeats                                       │
└──────────────────────────┬────────────────────────────────────┘
                           │
           ┌───────────────┼───────────────┐
           │               │               │
           ▼               ▼               ▼
    ┌──────────┐   ┌──────────┐   ┌──────────┐
    │  Main    │   │  Subagent│   │  Cron    │
    │  Session │   │  Session │   │  Jobs    │
    │  (chat)  │   │  (tasks) │   │          │
    └────┬─────┘   └────┬─────┘   └────┬─────┘
         │              │              │
         └──────────────┼──────────────┘
                        │
                        ▼
         ┌──────────────────────────────┐
         │     KNOWLEDGE GRAPH          │
         │     (Graphify)               │
         │  • graph.json                │
         │  • GRAPH_REPORT.md           │
         │  • Interactive HTML          │
         └──────────────┬───────────────┘
                        │
         ┌──────────────┼──────────────┐
         │              │              │
         ▼              ▼              ▼
    ┌────────┐   ┌────────┐   ┌────────┐
    │  MCP   │   │  Wiki  │   │  Search│
    │ Server │   │ Pages  │   │ Index  │
    │(tools) │   │(human) │   │(hybrid)│
    └────┬───┘   └────┬───┘   └────┬───┘
         │            │            │
         └────────────┴────────────┘
                      │
                      ▼
         ┌──────────────────────────────┐
         │      AGENT RESPONSE          │
         │  • Answers with citations    │
         │  • Suggests actions          │
         │  • Updates wiki/graph        │
         └──────────────────────────────┘
```

### MCP Server Registration
```json
{
  "mcpServers": {
    "graphify": {
      "command": ".../python",
      "args": ["-c", "from graphify.serve import serve; ..."],
      "description": "Graphify knowledge graph: query, explain, path"
    },
    "openclaw-wiki": {
      "command": ".../python3",
      "args": ["tools/mcp-server.py"],
      "description": "OpenClaw wiki: read, write, search, ingest, lint"
    }
  }
}
```

---

## Slide 13: Use Case — AVCPM Code Review

### Scenario
"Review my AVCPM project on GitHub. I want a comprehensive report."

### What Happened

```
1. INGEST
   ├─ Clone/sync repo
   ├─ Drop report into raw/
   └─ Graphify auto-indexes all code

2. REVIEW
   ├─ Spawn 4 specialized agents
   ├─ Each reads all source files
   └─ Returns structured review

3. COMPILE
   ├─ Merge 4 reports into unified document
   ├─ Priority matrix (P0/P1/P2)
   └─ Cross-cutting findings

4. PERSIST
   ├─ Save to reviews/
   ├─ Copy to raw/
   ├─ Ingest into wiki
   │   ├─ Source page
   │   ├─ Concept pages (code review, security audit, path traversal)
   │   └─ Entity page (AVCPM project)
   └─ Update index + log

5. PUSH
   └─ Commit + push to GitHub (rebased)
```

### Result
- **17,000-word report** with 19 findings
- **3 Critical** security vulnerabilities identified
- **Wiki updated** with 6 new pages
- **All changes version-controlled**

---

## Slide 14: Key Metrics Dashboard

```
┌─────────────────────────────────────────────────────────────┐
│                    SYSTEM METRICS                             │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  KNOWLEDGE GRAPH             │  WIKI                        │
│  • 2,251 nodes               │  • 16+ pages                 │
│  • 3,366 edges               │  • 4 categories               │
│  • 209 communities           │  • 78 documents indexed        │
│  • 86% high-confidence        │  • Learning Dashboard (Dataview)│
│                                                              │
│  AUTOMATION                  │  REVIEWS                     │
│  • 4 cron jobs active        │  • 4 specialized agents      │
│  • 6-hourly wiki checks      │  • 17,000-word report        │
│  • Daily graph updates       │  • 19 findings               │
│  • Weekly lint              │  • 8 P0 action items         │
│                                                              │
│  SELF-IMPROVING              │  LLM BACKEND                 │
│  • 9 errors logged           │  • 7 models available        │
│  • 5 resolved, 4 pending     │  • Ollama (local) + Cloud    │
│  • 7 performance baselines  │  • qwen3.6:35b (36B params)  │
│  • AGENTS.md learnings       │  • kimi-k2.6:cloud (default) │
│                                                              │
│  SEARCH                      │  STORAGE / BACKUP            │
│  • Hybrid semantic+keyword   │  • 2.4 MB backup             │
│  • 78 docs indexed          │  • 68 files backed up        │
│  • sqlite-vec backend       │  • GitHub secondary backup   │
│                                                              │
│  OBSIDIAN                    │                              │
│  • Vault opened              │                              │
│  • Dataview dashboard        │                              │
│  • Graph view enabled        │                              │
│  • Templates configured      │                              │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Slide 15: Lessons Learned

### What Worked
- ✅ **Graphify + LLM Wiki are complementary** — graph for structure, wiki for narrative
- ✅ **Cron jobs handle routine work** — agent only steps in for exceptions
- ✅ **Multi-agent reviews scale quality** — 4 focused eyes > 1 general eye
- ✅ **Ollama works for semantic extraction** — slow but functional and free
- ✅ **Git backup is essential** — `gh repo sync --force` taught us this the hard way
- ✅ **Self-improving skill adds structure** — `.learnings/` turns chaos into patterns

### What Didn't
- ⚠️ **Subagent timeouts** — 2-minute limit hit at 16 tool calls for large ingests
- ⚠️ **Ollama is slow** — qwen3.6:35b takes minutes; cloud LLM would be faster
- ⚠️ **Repo sync wipes local work** — need to use `git push` not `gh repo sync --force`
- ⚠️ **Search index needs manual rebuild** — no auto-trigger on file changes yet
- ⚠️ **Cron jobs documented but not verified** — assumed they were installed, needed check

### Open Questions
- ❓ Should we add a cloud LLM API key for faster semantic extraction?
- ❓ How often should full LLM extraction run vs AST-only updates?
- ❓ Should we export an Obsidian vault for visual browsing?
- ❓ When should we promote pending `.learnings/` to MEMORY.md?

---

## Slide 16: Future Roadmap

### Phase 4 Ideas

```
┌─────────────────────────────────────────────────────────────┐
│  SHORT TERM (This Week)                                     │
│  • Add cloud LLM API key (Gemini/Claude) for fast extract   │
│  • Populate .learnings/LEARNINGS.md with first insights   │
│  • Set up Obsidian Dataview dashboard                       │
│  • Auto-rebuild search index on file changes                │
├─────────────────────────────────────────────────────────────┤
│  MEDIUM TERM (This Month)                                   │
│  • Integrate email/calendar into heartbeat checks           │
│  • Build system metrics dashboard (Grafana/obsidian)          │
│  • Weekly .learnings/ review cron (promote to MEMORY.md)   │
│  • Create CI pipeline for graph + wiki updates              │
├─────────────────────────────────────────────────────────────┤
│  LONG TERM (This Quarter)                                   │
│  • Multiple workspace support (work, personal, projects)    │
│  • Agent-to-agent messaging for cross-workspace queries     │
│  • Automated P0 fix suggestions from code review findings   │
│  • Deploy to cloud for 24/7 operation                       │
└─────────────────────────────────────────────────────────────┘
```

---

## Slide 17: Q&A

**Resources:**
- Repository: https://github.com/pixy56/avcpm.git
- Wiki: `wiki/index.md` in workspace
- Graph: `graphify-out/graph.html` (open in browser)
- Learning Dashboard: `wiki/Learning-Dashboard.md` (requires Dataview)
- Reports: `reviews/AVCPM-CODE-REVIEW-2026-05-09.md`
- Self-Improving Report: `reviews/SELF-IMPROVING-AGENT-INTEGRATION-REPORT.md`

**Contact:** Matt via OpenClaw

---

*End of Presentation*
