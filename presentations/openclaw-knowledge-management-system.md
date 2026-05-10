# OpenClaw Knowledge Management System

**Presenter:** Matt  
**Date:** 2026-05-09  
**System:** OpenClaw + Graphify + LLM Wiki

---

## Slide 1: Executive Summary

**What We Built:** A fully automated, AI-powered personal knowledge management system that turns your workspace into a living, queryable knowledge base.

**Core Philosophy:**
- Human curates what goes in
- LLM does all maintenance
- Knowledge compounds over time

---

## Slide 2: Feature List

### Knowledge Capture
- ✅ **Raw Sources** — Drop articles, PDFs, transcripts, code into `raw/`
- ✅ **Auto-Ingest** — AI reads, summarizes, and files sources every 6 hours
- ✅ **GitHub Integration** — Pull code repos for analysis and review

### Knowledge Organization
- ✅ **Graphify Knowledge Graph** — Auto-extracts entities, relationships, clusters from all files
  - 2,251 nodes, 3,366 edges, 209 communities
  - 71.5× token reduction vs naive file-reading
- ✅ **LLM Wiki** — Markdown articles with `[[wikilinks]]` and YAML frontmatter
  - Sources, Concepts, Entities, Comparisons
- ✅ **Memory System** — Daily logs + curated long-term `MEMORY.md`

### Knowledge Retrieval
- ✅ **Semantic Search** — sqlite-vec + model2vec hybrid search (78 docs indexed)
- ✅ **Graph Queries** — BFS/DFS traversal of knowledge graph
- ✅ **Wiki Index** — Master index linking all pages
- ✅ **MCP Server** — Native `graph_query` tool for agents

### Automation
- ✅ **Daily Graph Updates** — `graphify update .` at 4:00 AM (AST-only, no API cost)
- ✅ **6-Hour Wiki Ingest** — Checks `raw/` for new sources
- ✅ **6-Hour Log Review** — Follows up on pending items
- ✅ **Weekly Lint** — Broken links, orphans, stale pages
- ✅ **Heartbeat Checks** — Periodic system maintenance

### Agent Team Coordination
- ✅ **Multi-Agent Reviews** — 4 specialized agents (Architecture, Security, Performance, Testing)
- ✅ **Unified Reports** — Compiled into single prioritized report
- ✅ **Wiki Integration** — Reports auto-ingested into knowledge base

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
└─────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────┐
│  LAYER 1: RAW SOURCES (raw/)        │
│  Immutable input                    │
│  • Articles, PDFs, transcripts        │
│  • Code repositories                │
│  • Research documents               │
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

## Slide 7: Component Deep Dive — Automation Layer

### Cron Jobs (4 Active)

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

## Slide 8: Component Deep Dive — Multi-Agent Review System

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

### AVCPM Review Results

| Reviewer | Runtime | Tokens | Key Finding |
|----------|---------|--------|-------------|
| Architecture | 1m21s | 221K | CLI/library conflation, non-unique commit IDs |
| Security | 4m2s | 110K | **3 Critical** path traversal vulnerabilities |
| Performance | 1m56s | 352K | No caching, no file locking, O(n²) operations |
| Testing | 2m2s | 385K | 5 modules untested, mixed frameworks |

---

## Slide 9: Integration Points

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

## Slide 10: Use Case — AVCPM Code Review

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

## Slide 11: Key Metrics Dashboard

```
┌─────────────────────────────────────────────────────────────┐
│                    SYSTEM METRICS                             │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  KNOWLEDGE GRAPH             │  WIKI                        │
│  • 2,251 nodes               │  • 16+ pages                 │
│  • 3,366 edges               │  • 4 categories               │
│  • 209 communities           │  • 78 documents indexed        │
│  • 86% high-confidence        │                              │
│                                                              │
│  AUTOMATION                  │  REVIEWS                     │
│  • 4 cron jobs active        │  • 4 specialized agents      │
│  • 6-hourly wiki checks      │  • 17,000-word report        │
│  • Daily graph updates       │  • 19 findings               │
│  • Weekly lint              │  • 8 P0 action items         │
│                                                              │
│  SEARCH                      │  STORAGE                     │
│  • Hybrid semantic+keyword   │  • 2.4 MB backup             │
│  • 78 docs indexed          │  • 68 files backed up        │
│  • sqlite-vec backend       │  • Full restore manifest     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Slide 12: Lessons Learned

### What Worked
- ✅ **Graphify + LLM Wiki are complementary** — graph for structure, wiki for narrative
- ✅ **Cron jobs handle routine work** — agent only steps in for exceptions
- ✅ **Multi-agent reviews scale quality** — 4 focused eyes > 1 general eye
- ✅ **Ollama works for semantic extraction** — slow but functional and free
- ✅ **Git backup is essential** — `gh repo sync --force` taught us this the hard way

### What Didn't
- ⚠️ **Subagent timeouts** — 2-minute limit hit at 16 tool calls for large ingests
- ⚠️ **Ollama is slow** — qwen3.6:35b takes minutes; cloud LLM would be faster
- ⚠️ **Repo sync wipes local work** — need to use `git push` not `gh repo sync --force`
- ⚠️ **Search index needs manual rebuild** — no auto-trigger on file changes yet

### Open Questions
- ❓ Should we add a cloud LLM API key for faster semantic extraction?
- ❓ How often should full LLM extraction run vs AST-only updates?
- ❓ Should we export an Obsidian vault for visual browsing?

---

## Slide 13: Future Roadmap

### Phase 4 Ideas

```
┌─────────────────────────────────────────────────────────────┐
│  SHORT TERM (This Week)                                     │
│  • Add cloud LLM API key (Gemini/Claude)                    │
│  • Set up Obsidian vault export                             │
│  • Auto-rebuild search index on file changes                │
│  • Add more sources to raw/ for testing                     │
├─────────────────────────────────────────────────────────────┤
│  MEDIUM TERM (This Month)                                   │
│  • Integrate email/calendar into heartbeat checks           │
│  • Build dashboard for system metrics                       │
│  • Add property-based tests for path sanitization           │
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

## Slide 14: Q&A

**Resources:**
- Repository: https://github.com/pixy56/avcpm.git
- Wiki: `wiki/index.md` in workspace
- Graph: `graphify-out/graph.html` (open in browser)
- Report: `reviews/AVCPM-CODE-REVIEW-2026-05-09.md`

**Contact:** Matt via OpenClaw

---

*End of Presentation*
