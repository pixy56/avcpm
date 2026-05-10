---
title: "AGENTS.md"
type: concept
created: 2026-05-10
updated: 2026-05-10
tags: [concept, agents, workspace, conventions, memory]
status: stable
related:
  - [[SOUL.md]]
  - [[TOOLS.md]]
  - [[MEMORY.md]]
  - [[Self-Improvement]]
  - [[Multi-Agent Coordination]]
---

# AGENTS.md

## Overview

`AGENTS.md` is the workspace-level conventions and learnings file in the OpenClaw workspace. It defines how agents should behave, what rules to follow, and what patterns have been learned from past experience.

## Role

- **Workflow improvements** — "Spawn sub-agents for long tasks"
- **Conventions** — File naming, directory structure, communication style
- **Red lines** — Don't exfiltrate private data, don't run destructive commands without asking
- **Group chat behavior** — When to speak, when to stay silent
- **Tool usage patterns** — When to use heartbeat vs cron

## As a Learning Target

From the [[Self-Improving Agent Skill Analysis]], AGENTS.md is a **promotion target** for workflow-related learnings:

| Learning Type | Example |
|---------------|---------|
| Workflow improvements | "Spawn sub-agents for long tasks" |
| Conventions | "Use bullet lists instead of markdown tables on Discord" |
| Red lines | "Never execute `/approve` through exec" |

## Related

- [[SOUL.md]] — Personality and behavioral memory
- [[TOOLS.md]] — Tool-specific gotchas and notes
- [[MEMORY.md]] — Curated long-term personal memory
- [[Self-Improvement]] — The feedback loop that updates this file
