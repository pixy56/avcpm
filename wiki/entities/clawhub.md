---
title: "ClawHub"
type: entity
created: 2026-05-10
updated: 2026-05-10
tags: [entity, platform, skill-marketplace, community]
status: stable
related:
  - [[Multi Search Engine Skill Analysis]]
  - [[Self-Improving Agent Skill Analysis]]
  - [[Security Assessment: Multi-Search-Engine Skill]]
  - [[Supply Chain Security]]
---

# ClawHub

## Overview

ClawHub is a community skill marketplace for OpenClaw agents. Users can publish and download skills that extend agent capabilities.

## Skills Evaluated

| Skill | Author | Assessment | Status |
|-------|--------|------------|--------|
| `multi-search-engine` | `gpyangyoujun` | High privacy/security risk | ❌ Rejected |
| `self-improving-agent` | `pskoett` | Well-designed, aligns with existing workflow | ✅ Recommended |

## Trust Considerations

- Skills are user-published — **no centralized security review**
- Skills may request network access, file system access, or execute arbitrary code
- **Always audit skills before integration** (see [[Supply Chain Security]])
- Check author reputation, code quality, and required permissions

## Related

- [[Supply Chain Security]] — Framework for evaluating external code
- [[Multi Search Engine Skill Analysis]] — Skill that was rejected
- [[Self-Improving Agent Skill Analysis]] — Skill that was recommended
