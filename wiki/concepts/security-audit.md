---
title: "Security Audit"
type: concept
created: 2026-05-09
updated: 2026-05-09
tags: [concept, security, audit, vulnerability, cryptography]
status: stable
related:
  - [[Code Review]]
  - [[AVCPM Code Review Report (2026-05-09)]]
  - [[Path Traversal]]
  - [[Cryptographic Signing]]
---

# Security Audit

## Definition

A specialized code review focused on identifying security vulnerabilities, unsafe patterns, input validation flaws, and cryptographic weaknesses in a codebase.

## Severity Classifications

| Level | Description | Examples |
|-------|-------------|----------|
| **Critical** | Exploitable remotely; immediate data/system compromise | Path traversal, arbitrary file write |
| **High** | Significant risk; exploitable with some conditions | Information disclosure, weak auth |
| **Medium** | Moderate risk; requires specific circumstances | Weak crypto parameters, TOCTOU |
| **Low** | Minor risk; defense-in-depth issues | Information leakage, inconsistency |

## Common Finding Categories

- **Input Validation** — Path traversal, injection, unsafe parsing
- **Authentication/Authorization** — Identity spoofing, session management
- **Cryptography** — Weak parameters, missing MAC, replay attacks
- **File System Safety** — Race conditions, symlink attacks, unsafe operations
- **Data Integrity** — Tampering, missing verification

## Related

- [[Path Traversal]] — Specific vulnerability type found in AVCPM
- [[Cryptographic Signing]] — Commit signing weaknesses found in AVCPM
- [[AVCPM Code Review Report (2026-05-09)]] — Full security audit results
