---
title: "AVCPM"
type: entity
created: 2026-05-09
updated: 2026-05-09
tags: [entity, project, avcpm, version-control, multi-agent]
status: stable
related:
  - [[AVCPM Code Review Report (2026-05-09)]]
  - [[Async Version Control]]
  - [[Multi-Agent Coordination]]
---

# AVCPM (Async Version Control Project Management)

## Overview

A multi-agent coordination system for software development. Allows multiple AI agents to collaborate on projects with task management, cryptographic identity, branch-based development, conflict detection, and code review workflows.

## Repository

https://github.com/pixy56/avcpm.git

## Architecture

| Phase | Features | Modules |
|-------|----------|---------|
| Phase 1 | Core infrastructure | task, commit, merge, validate, status |
| Phase 2 | Identity & dependencies | agent (RSA), task dependencies, signatures |
| Phase 3 | Advanced features | branching, diff, conflict, rollback, lifecycle, WIP |

## Code Review Status

**Date:** 2026-05-09
**Result:** Mixed — solid domain decomposition but critical security and performance issues
**Grade:** Architecture C+ | Security D+ | Performance C- | Testing B

## Key Issues

- 3 critical path traversal vulnerabilities
- No file locking (unsafe for multi-agent use)
- Library functions call `sys.exit()`
- Non-unique commit IDs
- 5 modules untested

## Related

- [[AVCPM Code Review Report (2026-05-09)]] — Full review
- [[Andrej Karpathy]] — Not related; placeholder for project history
