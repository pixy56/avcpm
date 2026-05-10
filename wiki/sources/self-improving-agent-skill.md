---
title: "Self-Improving Agent Skill Analysis"
type: source
created: 2026-05-09
updated: 2026-05-10
tags: [source, skill, clawhub, self-improvement, learning, memory]
status: stable
source_refs: [self-improving-agent-skill.md]
related:
  - [[Compounding Knowledge]]
  - [[Personal Knowledge Management]]
  - [[AGENTS.md]]
  - [[SOUL.md]]
  - [[TOOLS.md]]
  - [[MEMORY.md]]
---

# Self-Improving Agent Skill Analysis

## Source

`raw/self-improving-agent-skill.md` — Analysis of the ClawHub `self-improving-agent` skill (user `pskoett`).

## Summary

A skill for logging learnings and errors to structured markdown files for continuous improvement. Coding agents later process these into fixes, and important learnings get promoted to project memory files.

## Core Mechanism

1. **Log** → Capture errors, corrections, insights in structured markdown
2. **Review** → Periodically process logs for patterns
3. **Promote** → Move broadly applicable learnings to AGENTS.md, SOUL.md, TOOLS.md, MEMORY.md

## File Structure

```
.learnings/
├── LEARNINGS.md    # Corrections, insights, knowledge gaps, best practices
├── ERRORS.md       # Command failures, exceptions
└── FEATURE_REQUESTS.md  # User-requested capabilities
```

## Logging Format

Each entry includes:
- **ID:** `[LRN-YYYYMMDD-XXX]` or `[ERR-YYYYMMDD-XXX]`
- **Priority:** low | medium | high | critical
- **Status:** pending | resolved | promoted
- **Area:** frontend | backend | infra | tests | docs | config
- **Summary, Details, Suggested Action, Metadata**

## Promotion Targets

| Learning Type | Promote To | Example |
|---------------|-----------|---------|
| Behavioral patterns | SOUL.md | "Be concise, avoid disclaimers" |
| Workflow improvements | AGENTS.md | "Spawn sub-agents for long tasks" |
| Tool gotchas | TOOLS.md | "Git push needs auth configured first" |
| Knowledge gaps | MEMORY.md | "Graphify requires openai package for Ollama" |

## Integration with OpenClaw

- Uses existing workspace files (AGENTS.md, SOUL.md, TOOLS.md, MEMORY.md)
- Can use sessions tools for cross-session sharing
- Optional hook for session-start reminders

## Potential Improvements for Our System

1. Replace ad-hoc MEMORY.md updates with structured logging
2. Add `.learnings/` directory to workspace
3. Create cron job for periodic log review and promotion
4. Integrate with heartbeat checks
5. Use for tracking subagent timeout patterns
6. Use for tracking graphify/Ollama performance issues

## Assessment

This skill aligns well with the existing wiki/memory infrastructure. It formalizes a process that is already happening informally (MEMORY.md updates, AGENTS.md learnings). **Recommended for adoption** with integration into the existing `memory/` and `wiki/` workflow rather than creating a separate `.learnings/` directory.

## Full Analysis

See `raw/self-improving-agent-skill.md` for the original writeup.
