# AI Agent Knowledge Bases: Research Report
*Synthesized from three parallel research streams — April 30, 2026*

---

## Executive Summary

The AI agent knowledge base space has matured rapidly. What started as simple RAG (Retrieval-Augmented Generation) has evolved into a spectrum of approaches, from lightweight markdown-based personal wikis to production-grade hybrid vector+graph memory systems. Two particularly interesting points on that spectrum are **Andrej Karpathy's `llm-wiki.md` pattern** and **Obsidian.md** — the former as a compelling *design philosophy*, the latter as a mature *tooling platform* that happens to be remarkably agent-friendly.

The broader industry is converging on **hybrid architectures** (vector + graph + structured storage), but the markdown/wiki approach occupies a valuable niche: human-agent collaboration, portability, and zero infrastructure overhead.

---

## 1. Karpathy's `llm-wiki.md`: Compounding Knowledge

### What It Is

Published April 2026 as a GitHub Gist (5,000+ stars, 5,000+ forks within weeks), `llm-wiki.md` is not software — it's a **design pattern for self-maintaining personal knowledge bases**. Karpathy's core critique: most LLM document interactions (RAG, ChatGPT uploads, NotebookLM) are **stateless retrieval**. The model rediscovers knowledge from scratch every query. There is no compounding, no synthesis, no accumulation.

His alternative: instead of retrieving raw documents at query time, the LLM **incrementally builds and maintains a persistent, structured wiki** — a compounding artifact that sits between the user and raw sources.

### Three-Layer Architecture

| Layer | What It Is | Ownership |
|-------|-----------|-----------|
| **Raw Sources** | Immutable source documents (articles, papers, images, transcripts) | Human |
| **The Wiki** | LLM-generated markdown: summaries, entity pages, concept pages, analyses | LLM |
| **The Schema** | Configuration (`CLAUDE.md`, `AGENTS.md`) defining structure and workflows | Human + LLM |

### Core Workflows

**Ingest:**
1. Human drops source into `raw/`
2. LLM reads, discusses key takeaways
3. Creates source summary in `wiki/sources/`
4. Updates 10–15 affected entity/concept pages across the wiki
5. Updates `index.md`, `glossary.md`, `overview.md`
6. Appends to `log.md`

**Query:**
1. LLM reads `index.md` to find relevant pages
2. Reads those pages and synthesizes with citations
3. Good answers get filed back as new `analyses/` pages — explorations compound

**Lint (Maintenance):**
- Periodic checks for contradictions, stale claims, orphan pages, inconsistent terminology
- The human curates and directs; the LLM handles all filing and cross-referencing

### Key Pages & Conventions

- **`index.md`** — Content-oriented master catalog. The LLM reads this first on every query.
- **`log.md`** — Append-only chronological record with parseable prefixes (`grep`/`tail`-friendly).
- **`overview.md`** — High-level synthesis evolving with each ingest.
- **`glossary.md`** — Living terminology with canonical terms, deprecated variants, style rules.
- **Entity directories:** `sources/`, `features/`, `products/`, `personas/`, `concepts/`, `style/`, `analyses/`
- **Page format:** YAML frontmatter + one-line summary + structured body + `[[wiki-link]]` cross-references

### Historical Lineage

Karpathy explicitly links this to **Vannevar Bush's Memex (1945)** — a personal, curated knowledge store with associative trails. The unsolved problem then was maintenance burden; LLMs solve it by not getting bored and touching 15 files in one pass.

### Community Implementations

The pattern has spawned 15+ implementations showing how it's evolving:
- **balukosuri/llm-wiki-karpathy** — Ready-to-use template for Cursor + Obsidian with complete `CLAUDE.md` schema
- **Link (gowtham0992)** — Replaces `index.md` with an in-memory inverted token index + MCP server for scale
- **Origin (7xuanlu)** — Tauri + Rust desktop app with background daemon for between-session compounding

---

## 2. Obsidian.md: The Agent-Friendly Knowledge Platform

### What It Is

Obsidian is a **local-first, markdown-based knowledge management app**. Rather than a proprietary database, it stores plain text Markdown files in a local "vault." Free for personal use; paid tiers for Sync, Publish, and Commercial.

### Why It's Agent-Friendly

| Feature | Why It Matters for Agents |
|---------|------------------------|
| **File-based storage** | Every note is a `.md` file. No hidden database. Any script can read it. |
| **YAML frontmatter** | Structured metadata at the top of files — machine-readable without NLP. |
| **Wikilinks (`[[Note]]`)** | Explicit relationships between concepts, traversable by agents. |
| **Backlinks** | Bidirectional graph implicitly derived from links. |
| **Graph view** | Visualizes knowledge network — reveals clusters, orphans, hubs. |
| **Tags** | Inline categorical markers for filtering and organization. |

### AI/Agent Integration Ecosystem

**MCP Servers** (Model Context Protocol — open standard for tool access):
- `newtype-01/obsidian-mcp` (300+ stars)
- `aaronsb/obsidian-mcp-plugin` (289 stars)
- `cyanheads/obsidian-mcp-server` — comprehensive read/write/search/edit
- Multiple others in C#, JS, filesystem-based approaches

**Local REST API:**
- `coddingtonbear/obsidian-local-rest-api` (2,100+ stars) — secure HTTPS API for external scripts/agents

**Native CLI:**
- Official Obsidian CLI — `obsidian search`, `obsidian read`, `obsidian write`, `obsidian daily:append`, `obsidian eval`

**Agent-Specific Plugins:**
- `letta-ai/letta-obsidian` — Stateful AI agent with vault memory across sessions
- `rait-09/obsidian-agent-client` (1,700+ stars) — Agent Client Protocol (ACP) for Claude Code, Codex, Gemini CLI inside Obsidian
- `googlicius/obsidian-steward` — Vault-specific agent with fast search and terminal jumping
- `m-rgba/obsidian-ai-agent` — Claude Code integration

**Semantic Search & Embeddings:**
- `brianpetro/obsidian-smart-connections` (4,800+ stars) — Flagship AI plugin. On-device embeddings, semantic search, "chat with your notes"
- Hybrid retrieval stacks (BM25 + vector KNN via sqlite-vec/Model2Vec)

**Long-Term Memory:**
- `joshuaswarren/remnic` — Local-first memory for OpenClaw, Hermes, Codex, Claude Code using hybrid search (QMD)

### Strengths & Weaknesses as Agent KB

**Strengths:**
- Local-first & private — notes never leave the device
- Open format — no vendor lock-in, readable in 20 years
- Explicit graph structure via wikilinks/backlinks
- Multiple programmatic access paths (filesystem, REST, CLI, MCP)
- Human + agent share the same interface and data format
- Massive plugin ecosystem (Dataview for SQL-like queries, Tasks, Calendar, etc.)

**Weaknesses:**
- No native vector DB — requires plugins for semantic search
- Desktop-centric — mobile exists but is less automation-friendly
- App must be running for REST API / CLI integrations
- No built-in multi-agent orchestration — you wire up MCP/CLI yourself
- Vaults without indexing become "write-only databases" at scale
- Consistency depends on discipline (tags, links, frontmatter must be maintained)

---

## 3. The Broader Landscape: Tools, Patterns, & Tradeoffs

### Architectural Approaches

| Approach | Mechanism | Best For | Weakness |
|----------|-----------|----------|----------|
| **Vector-First** | Chunk + embed + similarity search | Broad semantic discovery | Loses explicit relationships; similarity ≠ correctness |
| **Graph-First** | Entities + relationships as nodes/edges | Relational reasoning, multi-hop queries | Higher complexity, extraction quality dependent |
| **Hybrid V+G** *(emerging default)* | Vector embeddings + graph structure | Production systems needing both | More infrastructure |
| **Structured Markdown** | Plain markdown + wikilinks + frontmatter | Human-agent collaboration, portability | Doesn't scale without indexing |
| **Multi-Model DB** | Doc + graph + vector + FTS in one query layer | Unified querying, reduced complexity | Newer, fewer mature options |

### Key Tools & Frameworks

**Memory-Layer Specialists:**

| Tool | Approach | Key Differentiator | Stars |
|------|----------|-------------------|-------|
| **Mem0** | Vector + optional graph (Mem0g) | Self-improving, 21+ framework integrations, LoCoMo benchmark leader | ~54K |
| **Zep / Graphiti** | Temporal knowledge graph | Tracks how facts change over time, 200ms retrieval | Production |
| **Letta** | Tiered memory (core/archival/recall) | Born from MemGPT (UC Berkeley), stateful agents with memory editing | ~22K |
| **Cognee** | Graph-vector hybrid (14 retrieval modes) | Six-stage pipeline (`cognify`), `memify` for self-improvement | Production |
| **LangMem** | LangGraph integration | Native to LangChain ecosystem | Mature |

**Infrastructure Layer:**
- **Vector DBs:** Chroma (dev-friendly, embeddable), Pinecone (managed, high-scale), Qdrant, pgvector, LanceDB (file-based, zero infra)
- **Graph DBs:** Neo4j + Agent Memory extension, FalkorDB (GraphRAG-optimized), Kuzu (embedded, file-based), Memgraph (in-memory)

### The Four Memory Types (Industry Consensus)

| Type | Function | Storage | Failure Mode |
|------|----------|---------|--------------|
| **Short-term / Working** | Context window contents | In-context | Context overflow, silent truncation |
| **Episodic** | Past events, interaction history | Database + retrieval | Raw transcripts expensive; summaries lossy |
| **Semantic** | Atemporal facts, knowledge base | Vector/graph DB | Similarity ≠ correctness; stale embeddings |
| **Procedural** | How to do things, workflows | System prompts, few-shot examples | Agent behavioral drift if self-updating |

### Retrieval vs. Structured Storage

- **RAG (Retrieval):** Best for large, evolving corpora. Bottleneck: retrieval quality.
- **Structured (Graph/DB):** Best for relational reasoning, entity histories, multi-hop queries. Bottleneck: setup/maintenance.
- **2026 Consensus:** Hybrid is the production default. Vectors for semantic discovery, graphs for relational reasoning.

### Performance Reality Check (LoCoMo Benchmark)

The LoCoMo benchmark is the de facto standard for long-term conversational memory:
- **Full-context baseline:** 72.9% accuracy, but ~26K tokens/conversation and 17s latency
- **Mem0g (graph-enhanced):** 68.4% accuracy with 91% lower latency and 90% fewer tokens
- The tradeoff is real: ~5-7% accuracy loss for massive efficiency gains

---

## 4. Synthesis: How These Pieces Fit Together

### The Markdown Niche

Karpathy's `llm-wiki.md` and Obsidian occupy a specific, valuable position in the knowledge base spectrum:

| Dimension | `llm-wiki.md` + Obsidian | Mem0 / Zep / Cognee |
|-----------|-------------------------|---------------------|
| **Portability** | Plain text — readable anywhere | Requires specific DB/backend |
| **Human readability** | Native — humans and agents share format | Opaque — humans need tools to inspect |
| **Infrastructure** | Zero — just markdown files | Vector DB, graph DB, or both |
| **Scale** | Hundreds of pages without indexing; thousands with hybrid search | Millions of facts natively |
| **Relational reasoning** | Explicit via wikilinks; limited without graph engine | Native multi-hop traversal |
| **Agent maintenance** | LLM maintains markdown directly | Specialized memory operations API |
| **Version control** | Native git support | Requires DB migration strategies |

### The Convergence Pattern

The most interesting development is how these approaches are **converging** rather than competing:

1. **Markdown as the ingestion layer:** Start with structured markdown (Karpathy pattern) for human-agent collaboration and portability.
2. **Index for scale:** Add hybrid search (BM25 + vector, e.g., `qmd` or `Smart Connections`) when the vault grows.
3. **Graph extraction for relational queries:** Use tools like Cognee or Neo4j's Agent Memory to extract entity-relationship graphs from markdown for deep reasoning.
4. **MCP for agent integration:** Expose the vault to any agent via MCP servers, REST APIs, or CLI.

This gives you:
- **Human layer:** Obsidian for browsing, editing, visualizing
- **Agent layer:** MCP/CLI for read/write/search
- **Search layer:** Hybrid BM25 + vector for fast retrieval
- **Reasoning layer:** Optional graph extraction for multi-hop queries
- **Storage layer:** Git-tracked markdown files — fully portable, fully inspectable

### Practical Recommendations

**For personal / small-team use:**
- Start with the Karpathy pattern in an Obsidian vault
- Use Smart Connections for semantic search once you hit ~100+ notes
- Wire up an MCP server (e.g., `obsidian-mcp`) for agent access
- Let the LLM maintain the wiki via ingest/query/lint workflows

**For production / scale:**
- Evaluate Mem0g or Cognee as the memory layer
- Use markdown/wiki as the human-facing surface, with automatic sync to the vector/graph backend
- Consider Zep/Graphiti if tracking how facts evolve over time is critical
- Implement tiered memory (Letta-style: core + archival + recall) for latency-sensitive agents

**For this OpenClaw workspace:**
- The existing markdown-based memory system (`memory/`, `MEMORY.md`) is already aligned with the Karpathy pattern
- Adding structured frontmatter to memory files would make them more machine-readable
- Wikilinks between memory files would create an explorable knowledge graph
- A hybrid search layer (`qmd` or similar) could be added when the corpus scales

---

## 5. Key Takeaways

1. **Compounding beats retrieval.** Karpathy's core insight — maintaining a structured, cross-referenced wiki rather than re-deriving structure on every query — is architecturally sound and increasingly validated by the industry move toward persistent memory layers.

2. **Markdown is underrated as an agent format.** Plain text + YAML frontmatter + wikilinks gives you human readability, machine parseability, version control, and zero infrastructure. The gap vs. vector/graph DBs is scale and relational reasoning — both bridgeable with indexing and extraction layers.

3. **Obsidian is the most mature "human-agent shared interface."** Its file-based model, graph visualization, and exploding AI plugin ecosystem make it the best current platform for collaborative human-LLM knowledge work.

4. **Hybrid is the production default.** The 2026 consensus is vector + graph + structured storage. But the *entry point* can be as simple as a git repo of markdown — and for many use cases, that's sufficient.

5. **Benchmarks matter.** The LoCoMo results show that full-context is technically best (~73%) but impractical. Smart memory layers (Mem0g ~68%) achieve near-parity with massive efficiency gains. The gap is small and closing.

6. **MCP is the integration standard.** Model Context Protocol has become the dominant way to give agents tool access to external systems, including Obsidian vaults. Any knowledge base strategy should consider MCP compatibility.

---

*Report compiled by Claw 🐾 | Sources: web search, GitHub repos, arXiv papers, project documentation*
