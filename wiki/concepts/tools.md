---
title: "TOOLS.md"
type: concept
created: 2026-05-10
updated: 2026-05-10
tags: [concept, tools, workspace, notes, configuration]
status: stable
related:
  - [[AGENTS.md]]
  - [[SOUL.md]]
  - [[MEMORY.md]]
  - [[Self-Improvement]]
---

# TOOLS.md

## Overview

`TOOLS.md` is the local tool configuration and notes file in the OpenClaw workspace. It stores environment-specific details that are unique to this setup — the stuff that skills don't know about.

## What Goes Here

- Camera names and locations
- SSH hosts and aliases
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- LLM backend configuration (Ollama host, models, keep-alive)
- MCP server configuration
- Anything environment-specific

## As a Learning Target

From the [[Self-Improving Agent Skill Analysis]], TOOLS.md is a **promotion target** for tool-specific learnings:

| Learning Type | Example |
|---------------|---------|
| Gotchas | "Git push needs auth configured first" |
| Configuration | "Ollama keep-alive: 30 minutes" |
| Preferences | "Preferred voice: Nova (warm, slightly British)" |

## Relationship to Skills

> Skills define _how_ tools work. This file is for _your_ specifics.

Keeping them separate means you can update skills without losing your notes, and share skills without leaking your infrastructure.

## Related

- [[AGENTS.md]] — Workspace conventions and learnings
- [[SOUL.md]] — Personality and behavioral memory
- [[MEMORY.md]] — Curated long-term personal memory
- [[Self-Improvement]] — The feedback loop that updates this file
