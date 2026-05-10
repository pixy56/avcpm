---
title: "Path Traversal"
type: concept
created: 2026-05-09
updated: 2026-05-09
tags: [concept, security, vulnerability, path-traversal, cwe-22]
status: stable
related:
  - [[Security Audit]]
  - [[AVCPM Code Review Report (2026-05-09)]]
  - [[Input Validation]]
---

# Path Traversal (CWE-22)

## Definition

A security vulnerability where user-supplied input is used to construct file paths without proper sanitization, allowing an attacker to access files outside the intended directory.

## Common Patterns

| Vulnerable | Safe |
|-----------|------|
| `os.path.join(base, user_input)` | Validate against allowlist: `^[A-Za-z0-9_-]+$` |
| `open(user_input, 'r')` | `sanitize_path(user_input, base_dir)` |
| `shutil.move(src, dst)` | Ensure both resolve within `base_dir` |

## AVCPM Findings

The AVCPM codebase had **3 critical** path traversal vulnerabilities:
1. **Task ID traversal** — `avcpm_task.py`: `task_id` concatenated into paths directly
2. **Rollback/restore traversal** — `avcpm_rollback.py`: commit metadata `file` field used as destination
3. **Merge staging traversal** — `avcpm_merge.py`: `staging_path` from ledger used directly

## Related

- [[Security Audit]] — Full audit context
- [[Input Validation]] — General prevention strategy
