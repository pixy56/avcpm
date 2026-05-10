---
title: "Privacy Risk"
type: concept
created: 2026-05-10
updated: 2026-05-10
tags: [concept, privacy, security, risk-assessment]
status: stable
related:
  - [[Security Audit]]
  - [[Supply Chain Security]]
  - [[Terms of Service Compliance]]
  - [[Multi Search Engine Skill Analysis]]
  - [[Security Assessment: Multi-Search-Engine Skill]]
---

# Privacy Risk

## Definition

Privacy risk in the context of AI agent systems refers to the potential for unauthorized exposure, collection, or misuse of personal data, queries, or behavioral patterns when using external services, APIs, or network-connected tools.

## Key Dimensions

### Query Exposure
When an agent sends user queries to third-party services, those queries may contain:
- Personally Identifiable Information (PII)
- Proprietary research or business data
- Medical, legal, or financial questions
- Location or behavioral patterns

### Data Retention
Different services have different retention policies:
- Some log indefinitely by IP address
- Some aggregate and anonymize after a period
- Some share with affiliates or advertisers

### Fingerprinting
Even without explicit cookies, automated request patterns can be identified through:
- TLS fingerprinting
- Request timing and sequencing
- Header combinations
- Behavioral analysis

## Assessment Framework

| Level | Description | Example |
|-------|-------------|---------|
| 🟢 LOW | No external data exposure | Local-only processing (Graphify + Ollama) |
| 🟡 MEDIUM | Limited exposure with controls | Official API with query sanitization |
| 🟠 MEDIUM-HIGH | Significant exposure, some mitigations | Single engine with session cookies |
| 🔴 HIGH | Massive exposure, minimal controls | 16 engines receiving raw queries simultaneously |

## Mitigation Strategies

1. **Prefer local processing** — Keep sensitive data on-device when possible
2. **Query sanitization** — Strip PII before sending to external services
3. **Network sandboxing** — Run untrusted tools in isolated containers
4. **VPN/Tor egress** — Mask origin IP for non-sensitive queries
5. **Aggressive caching** — Minimize repeated identical queries
6. **Official APIs** — Use ToS-compliant APIs with documented data handling

## Related

- [[Security Assessment: Multi-Search-Engine Skill]] — Real-world privacy risk case study
- [[Supply Chain Security]] — Code trust and data handling
- [[Terms of Service Compliance]] — Legal frameworks governing data use
