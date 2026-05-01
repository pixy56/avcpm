---
title: "MCP Protocol"
type: concept
created: 2026-05-01
updated: 2026-05-01
tags: ["mcp", "integration", "protocol"]
---

# MCP Protocol

Model Context Protocol (MCP) is an open standard for giving AI tools
structured access to external data and systems.

## How It Works
- Servers expose "tools" with schemas
- Clients (agents) discover and call tools via JSON-RPC
- Transport: stdio (local) or HTTP (remote)

## This Workspace
- Server: `tools/mcp-server.py`
- Config: `~/.openclaw/mcp-config.json`
- 7 wiki tools available

## See Also
- [[entities/obsidian-md]] — Obsidian MCP integrations
- [[analyses/convergence-implementation]]
