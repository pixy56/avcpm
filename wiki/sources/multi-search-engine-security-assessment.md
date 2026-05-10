---
title: "Security Assessment: Multi-Search-Engine Skill"
type: source
created: 2026-05-09
updated: 2026-05-10
tags: [source, security, assessment, search-engine, privacy, ethics]
status: stable
source_refs: [multi-search-engine-security-assessment.md]
related:
  - [[Multi Search Engine Skill Analysis]]
  - [[Security Audit]]
  - [[Privacy Risk]]
  - [[Terms of Service Compliance]]
  - [[Brave Search API]]
---

# Security Assessment: Multi-Search-Engine Skill

## Source

`raw/multi-search-engine-security-assessment.md` — Privacy & Security Analyst subagent review.

## Summary

A comprehensive security and privacy assessment of the `multi-search-engine` skill from ClawHub (user `gpyangyoujun`). The analyst **recommends against integration**, citing high privacy risk (16× query exposure), high ethical risk (systematic ToS violations across all 16 engines), and moderate security risk (untrusted code, XSS potential, IP blocking).

## Key Findings

| Category | Risk | Detail |
|----------|------|--------|
| Query Exposure | 🔴 HIGH | Every query sent to 16 third-party servers |
| ToS Compliance | 🔴 HIGH | Explicitly designed to circumvent API keys and access controls |
| Supply Chain | 🟠 MEDIUM-HIGH | Untrusted external code with full network access |
| Fingerprinting | 🟡 MEDIUM | Automated patterns detectable; cookies correlate sessions |
| XSS/Injection | 🟡 MEDIUM | Untrusted HTML consumed without sanitization |
| Rate Limiting | 🟡 MEDIUM | Inadequate delays; likely CAPTCHA/block |

## Recommendations

1. **Reject** the multi-search-engine skill for main workspace integration.
2. **Adopt Brave Search API** if real-time web data is needed — proper API, free tier, ToS-compliant.
3. **Maintain local-only baseline** (Graphify + Ollama) for sensitive or routine queries.
4. **Audit any future skill** with network access before integration.
5. **Use manual `web_fetch`** for one-off wiki source discovery instead of automated meta-search.

## Comparison to Current System

| Dimension | Current (Graphify + Ollama) | Proposed (Multi-Search) |
|-----------|----------------------------|------------------------|
| Data locality | ✅ All local | ❌ 16 external servers |
| Privacy | ✅ No tracking | ❌ Full exposure |
| ToS compliance | ✅ None involved | ❌ Violates all 16 |
| Security surface | ✅ Local-only | ❌ Untrusted code, XSS, MITM |
| Real-time data | ❌ Limited | ✅ Fresh web results |
| Cross-validation | ❌ Single source | ✅ Multi-engine |

## Full Report

See `raw/multi-search-engine-security-assessment.md` for the complete assessment with risk ratings matrix, mitigation strategies, and appendices.
