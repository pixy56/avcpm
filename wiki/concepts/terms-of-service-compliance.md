---
title: "Terms of Service Compliance"
type: concept
created: 2026-05-10
updated: 2026-05-10
tags: [concept, ethics, legal, compliance, risk-assessment]
status: stable
related:
  - [[Privacy Risk]]
  - [[Supply Chain Security]]
  - [[Security Assessment: Multi-Search-Engine Skill]]
  - [[Multi Search Engine Skill Analysis]]
---

# Terms of Service Compliance

## Definition

Terms of Service (ToS) compliance refers to the adherence to the legal agreements and usage policies set by service providers. In the context of AI agent tools and skills, it means ensuring that automated systems interact with third-party services only in ways that are explicitly permitted.

## Why It Matters

### Legal Risk
- Violating ToS can result in account termination
- Some jurisdictions may treat systematic ToS violations as legal breaches
- Commercial use without proper authorization can lead to liability

### Ethical Risk
- ToS often exist to prevent abuse of shared infrastructure
- Circumventing access controls externalizes costs to service providers
- Systematic scraping undermines the business model of free services

### Operational Risk
- Services actively detect and block ToS violations
- IP addresses may be blacklisted
- CAPTCHA walls and rate limits disrupt legitimate workflows

## Common Violations in Agent Tools

| Violation | Example | Risk |
|-----------|---------|------|
| Automated scraping | Sending automated requests to search engines without API keys | IP block, legal notice |
| API key circumvention | Using web scraping to avoid paid API tiers | Account termination |
| Rate limit evasion | Spreading requests across IPs or using delays to bypass limits | Blacklisting |
| Data harvesting | Bulk collection of content against robots.txt or ToS | Legal action |

## Assessment Framework

| Level | Description |
|-------|-------------|
| ✅ Compliant | Uses official APIs, respects rate limits, follows robots.txt |
| ⚠️ Gray Area | Self-hosted proxies (SearXNG), personal use only |
| ❌ Violation | Systematic scraping, API circumvention, ignores rate limits |

## Related

- [[Security Assessment: Multi-Search-Engine Skill]] — Case study of a skill explicitly architected to violate ToS
- [[Privacy Risk]] — Privacy implications of non-compliant integrations
- [[Supply Chain Security]] — Evaluating external tools for compliance
