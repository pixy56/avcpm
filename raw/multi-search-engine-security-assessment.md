# Security Assessment: Multi-Search-Engine Skill

**Analyst:** Privacy & Security Analyst (Subagent)  
**Date:** 2026-05-09  
**Source:** https://clawhub.ai/gpyangyoujun/multi-search-engine  
**Baseline:** Local Graphify + Ollama (no external search)

---

## Executive Summary

**RECOMMENDATION: DO NOT INTEGRATE** as-is.

This skill is designed to scrape 16 search engines without API keys by mimicking browser traffic, acquiring session cookies dynamically, and circumventing access controls. It introduces **high privacy risk** (16× query exposure), **high ethical risk** (clear ToS violations across all major engines), and **moderate security risk** (untrusted code, XSS potential, IP blocking). The current local-only system provides a strong privacy baseline that this skill would fundamentally undermine.

---

## 1. Privacy Risks

### 1.1 Search Query Exposure — **RISK: HIGH**

| Aspect | Assessment |
|--------|------------|
| Query distribution | Every query sent to **16 third-party servers** simultaneously |
| Data sensitivity | Raw search terms may contain PII, proprietary research, medical queries, legal questions |
| Encryption | HTTPS used, but queries are visible to destination servers and any SSL-inspecting proxy |
| Logging | All engines (Google, Baidu, Bing, etc.) log queries by IP address indefinitely |
| Current baseline | Graphify + Ollama: **zero external query exposure** — all processing is local |

**Impact:** A single sensitive query (e.g., "symptoms of [condition] site:mycompany.com filetype:pdf") is logged by 16 different organizations, each with different data retention and jurisdiction policies (US, EU, China).

### 1.2 Browser Fingerprinting — **RISK: MEDIUM**

- Skill uses "standard browser headers" but automated request patterns (fixed delays, identical header sets, sequential batched execution) are trivially distinguishable from organic traffic.
- Search engines use TLS fingerprinting, JavaScript challenge pages, and behavioral analysis to detect automation.
- Risk: engines can flag the originating IP as a bot, potentially affecting normal browsing from the same network.

### 1.3 Cookie-Based Tracking — **RISK: MEDIUM-HIGH**

- Skill acquires session cookies from engine homepages on-demand.
- Even "session-only" cookies enable **query correlation** across a session.
- If any engine sets persistent cookies (despite claims of session-only), tracking extends beyond the session.
- Cookies are "memory-only" — but memory is readable by the process and any compromise.

### 1.4 IP Address Profiling — **RISK: MEDIUM**

- All requests originate from Matt's static/residential IP.
- 16 engines can independently correlate this IP with query history.
- Repeated use creates a behavioral profile tied to the IP address.

---

## 2. Security Risks

### 2.1 Supply Chain / Code Trust — **RISK: MEDIUM-HIGH**

| Issue | Detail |
|-------|--------|
| Source | ClawHub user `gpyangyoujun` — no prior trust relationship |
| Code review | None performed; skill downloaded as opaque package |
| Capability | Has full network access, cookie manipulation, and HTML parsing |
| Risk | Could exfiltrate queries, cookies, or local data to an unknown endpoint disguised as a "search engine" |

### 2.2 XSS / Content Injection — **RISK: MEDIUM**

- Search results are untrusted HTML from the open web.
- If results are rendered in any UI or passed to downstream tools without sanitization, malicious results could inject payloads.
- Search engines themselves are high-value targets; poisoned results are a known attack vector.

### 2.3 Man-in-the-Middle — **RISK: LOW**

- HTTPS is used for all engines.
- However, no certificate pinning is mentioned.
- If the network has SSL inspection (corporate proxy, ISP), queries are decrypted and logged.

### 2.4 Rate Limiting & Blocking — **RISK: MEDIUM**

- Claimed rate limit: 1–2 seconds between requests, 3–4 engines per batch.
- This is **insufficient** for 16 engines. Google, Bing, and Baidu aggressively rate-limit unauthenticated scraping.
- Likely outcomes: CAPTCHA triggers, temporary IP blocks, or permanent blacklisting.
- An IP block could affect normal use of these services from the same network.

### 2.5 Credential Leakage via Cookies — **RISK: MEDIUM**

- If the user is logged into any search engine in a browser on the same machine, session cookies might overlap or be acquired in a way that links the automated queries to the user's authenticated identity.
- No mention of cookie isolation or containerization.

---

## 3. Ethical Concerns

### 3.1 Terms of Service Violations — **RISK: HIGH**

| Engine | ToS Stance on Scraping |
|--------|------------------------|
| Google | Prohibits automated scraping; requires API keys |
| Bing | Prohibits unauthorized automated access |
| Baidu | Prohibits non-API automated collection |
| DuckDuckGo | Tolerates light scraping but not systematic automation |
| Yahoo / Startpage / Brave / Ecosia / Qwant | All prohibit automated scraping in ToS |

The skill's own documentation says *"Users are responsible for complying with search engine ToS"* — this is a liability shield, not an ethical design. The tool is **explicitly architected** to violate ToS at scale.

### 3.2 "No API Keys Required" — **RISK: HIGH**

- Framed as a feature, this is actually a **deliberate circumvention** of access controls.
- API keys exist for accountability, rate limiting, and proper terms of use.
- Bypassing them is analogous to using a backdoor instead of the front door.

### 3.3 Infrastructure Impact — **RISK: MEDIUM**

- 16 engines × retries × batches = significant load on third-party infrastructure.
- The skill is a **distributed scraping operation** disguised as a convenience tool.
- No mention of `robots.txt` parsing in the actual workflow (despite the claim).

### 3.4 False Privacy Claims — **RISK: MEDIUM**

- "Privacy-focused" labels for DuckDuckGo, Startpage, etc. are misleading in this context.
- While these engines don't track users themselves, the *skill* is still sending queries to them in an automated, fingerprintable way.
- The privacy benefit of the engine is negated by the automation pattern.

---

## 4. Comparison: Current System vs. Proposed Skill

| Dimension | Current (Graphify + Ollama) | Proposed (Multi-Search) |
|-----------|----------------------------|------------------------|
| **Data locality** | ✅ All data stays local | ❌ Queries sent to 16 external servers |
| **Privacy** | ✅ No tracking, no cookies, no IP logging | ❌ Full query exposure, cookie tracking |
| **ToS compliance** | ✅ No external ToS involved | ❌ Violates ToS of all 16 engines |
| **Security surface** | ✅ Local-only, no network egress | ❌ Untrusted code, XSS risk, MITM exposure |
| **Rate limiting** | ✅ N/A | ❌ Inadequate, likely to trigger blocks |
| **Real-time data** | ❌ Limited to indexed sources | ✅ Fresh web results |
| **Cross-validation** | ❌ Single source of truth | ✅ Multi-engine comparison |
| **Cost** | ✅ Free (local compute) | ✅ Free (but externalized cost to engines) |

**Trade-off:** The skill adds real-time web access and cross-engine validation at the cost of **fundamentally compromising** the privacy-first, local-only architecture of the current system.

---

## 5. Mitigation Strategies

### 5.1 Recommended Alternative: Use Official APIs

| Service | Free Tier | ToS-Compliant | Privacy Notes |
|---------|-----------|---------------|---------------|
| **Brave Search API** | 2,000 queries/month | ✅ Yes | Independent index, privacy-respecting |
| **Google Custom Search** | 100 queries/day | ✅ Yes | Requires API key, logged by Google |
| **Bing Web Search API** | 1,000 queries/month | ✅ Yes | Microsoft ecosystem |
| **DuckDuckGo** | No official API | N/A | HTML scraping still violates ToS |
| **SearXNG (self-hosted)** | Unlimited | ⚠️ Gray area | Open-source meta-search; still proxies to engines |

**Best option:** Brave Search API. It has a generous free tier, is ToS-compliant, and aligns with privacy values.

### 5.2 If Integration Is Required Despite Risks

| Mitigation | Implementation | Effectiveness |
|------------|----------------|---------------|
| **Fork & audit** | Review all code before execution; look for exfiltration | HIGH |
| **Strip engines** | Limit to 2–3 privacy-focused engines (DDG, Startpage, Brave) | MEDIUM |
| **Query sanitization** | Strip PII, use abstracted/generic queries | MEDIUM |
| **Aggressive caching** | 24h+ TTL to minimize repeated queries | MEDIUM |
| **Network sandbox** | Run in isolated container; restrict egress to necessary domains | HIGH |
| **VPN/Tor egress** | Route traffic through VPN to mask origin IP | LOW-MEDIUM |
| **No sensitive queries** | Never use for personal, medical, legal, or proprietary research | HIGH |

### 5.3 Do Not Do

- ❌ Do not run on a network where IP reputation matters (e.g., if Matt works from home and the IP is shared).
- ❌ Do not use for queries containing PII, proprietary data, or sensitive research.
- ❌ Do not run unattended or in a cron job — this amplifies ToS violation and fingerprinting.
- ❌ Do not trust the "memory-only cookies" claim without verifying the code.

---

## 6. Risk Ratings Matrix

| Risk ID | Category | Subcategory | Rating | Justification |
|---------|----------|-------------|--------|---------------|
| PRI-01 | Privacy | Query Exposure | 🔴 HIGH | 16 third parties receive raw queries |
| PRI-02 | Privacy | Fingerprinting | 🟡 MEDIUM | Automated patterns detectable; cookies correlate |
| PRI-03 | Privacy | Data Retention | 🔴 HIGH | All engines log indefinitely by IP |
| SEC-01 | Security | Supply Chain | 🟠 MEDIUM-HIGH | Untrusted external code; full network access |
| SEC-02 | Security | XSS/Injection | 🟡 MEDIUM | Untrusted HTML consumed without sanitization |
| SEC-03 | Security | MITM | 🟢 LOW | HTTPS used; SSL inspection is edge case |
| SEC-04 | Security | Rate Limiting | 🟡 MEDIUM | Inadequate delays; likely CAPTCHA/block |
| SEC-05 | Security | Cookie Leakage | 🟡 MEDIUM | No isolation from browser sessions |
| ETH-01 | Ethics | ToS Compliance | 🔴 HIGH | Explicitly designed to violate ToS |
| ETH-02 | Ethics | API Circumvention | 🔴 HIGH | Bypasses access controls by design |
| ETH-03 | Ethics | Infrastructure | 🟡 MEDIUM | Distributed scraping load on 16 engines |
| ETH-04 | Ethics | False Claims | 🟡 MEDIUM | "Respects robots.txt" and "privacy-focused" are misleading |

---

## 7. Final Recommendations

1. **REJECT the multi-search-engine skill** for integration into the main workspace. The privacy and ethical risks outweigh the benefits.

2. **ADOPT Brave Search API** (or similar) as the sole external search integration if real-time web data is needed. It provides a proper API, free tier, and ToS-compliant access.

3. **MAINTAIN the local-only baseline** for all sensitive or routine queries. Graphify + Ollama should remain the default.

4. **AUDIT any future skill** from ClawHub or external sources before integration. Skills with network access should be treated as untrusted code.

5. **IF web search is needed for wiki source discovery**, use manual, one-off `web_fetch` calls to specific, trusted URLs rather than automated meta-search scraping.

---

## Appendices

### A. References
- Source skill: https://clawhub.ai/gpyangyoujun/multi-search-engine
- Current system: `raw/llmwiki-vs-graphify.md`, `MEMORY.md`
- Brave Search API: https://api.search.brave.com/

### B. Glossary
- **ToS:** Terms of Service  
- **PII:** Personally Identifiable Information  
- **XSS:** Cross-Site Scripting  
- **MITM:** Man-in-the-Middle  
- **SearXNG:** Self-hosted meta-search engine
