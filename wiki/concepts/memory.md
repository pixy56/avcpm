---
title: "MEMORY.md"
type: concept
created: 2026-05-10
updated: 2026-05-10
tags: [concept, memory, long-term, personal, wiki]
status: stable
related:
  - [[AGENTS.md]]
  - [[SOUL.md]]
  - [[TOOLS.md]]
  - [[Self-Improvement]]
  - [[Compounding Knowledge]]
  - [[Personal Knowledge Management]]
---

# MEMORY.md

## Overview

`MEMORY.md` is the curated long-term memory file for the AI assistant in the OpenClaw workspace. It contains the distilled essence of what the agent has learned — not raw logs, but the wisdom worth keeping.

## Role

- **Curated wisdom** — Decisions, context, things to remember
- **Personal context** — Only loaded in main sessions, not in group chats
- **Cross-session continuity** — Survives session restarts
- **Security-sensitive** — Contains personal context that shouldn't leak

## Contents

- Significant events and decisions
- Lessons learned from mistakes
- User preferences and patterns
- Knowledge gaps to fill
- Project context and status

## As a Learning Target

From the [[Self-Improving Agent Skill Analysis]], MEMORY.md is a **promotion target** for knowledge gap learnings:

| Learning Type | Example |
|---------------|---------|
| Knowledge gaps | "Graphify requires openai package for Ollama" |
| Lessons learned | "Don't use sys.exit() in library functions" |
| User preferences | "Matt prefers direct, factual communication" |

## Maintenance

Periodically (every few days), review recent `memory/YYYY-MM-DD.md` files and update MEMORY.md with distilled learnings. Think of it like a human reviewing their journal and updating their mental model.

## Related

- [[AGENTS.md]] — Workspace conventions and learnings
- [[SOUL.md]] — Personality and behavioral memory
- [[TOOLS.md]] — Tool-specific gotchas and notes
- [[Self-Improvement]] — The feedback loop that updates this file
- [[Personal Knowledge Management]] — The broader system
