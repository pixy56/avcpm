#!/usr/bin/env python3
"""Weekly wiki health check — broken links, orphans, stale pages."""

from pathlib import Path
import re
from datetime import datetime

VAULT = Path.home() / ".openclaw/workspace/wiki"



import unicodedata


def normalize_slug(name):
    """Normalize a wikilink target into a comparable slug."""
    # Handle paths like sources/foo → foo
    name = name.split('/')[-1]
    # Strip optional display text: [[target|Display]] → target
    name = name.split('|')[0]
    slug = re.sub(r'[^a-z0-9]+', '-', name.lower().strip()).strip('-')
    return slug


# Shared alias mapping: display_name → canonical_slug
ALIASES = {
    'wikilinks': 'wikilink',
    'obsidian': 'obsidian-md',
    'karpathy-llm-wiki-gist': 'karpathy-llm-wiki',
    'llm-wiki-vs-graphify-comparing-pkm-approaches': 'llmwiki-vs-graphify',
    'avcpm-code-review-report-2026-05-09': 'avcpm-code-review-2026-05-09',
    'llm-wiki-vs-graphify': 'llmwiki-vs-graphify',
    'graphify-tool': 'graphify',
    'async-version-control': 'avcpm',
    'performance-review': 'code-review',
    'testing-review': 'code-review',
    'input-validation': 'security-audit',
    'cryptographic-signing': 'security-audit',
    'multi-search-engine-skill-analysis': 'multi-search-engine-skill',
    'security-assessment-multi-search-engine-skill': 'multi-search-engine-security-assessment',
    'self-improving-agent-skill-analysis': 'self-improving-agent-skill',
    'agents': 'agents',
    'agents-md': 'agents',
    'soul': 'soul',
    'soul-md': 'soul',
    'tools': 'tools',
    'tools-md': 'tools',
    'memory': 'memory',
    'memory-md': 'memory',
    'terms-of-service-compliance': 'terms-of-service-compliance',
    'terms-of-service': 'terms-of-service-compliance',
}
# Reverse map for orphan detection: canonical_slug → set of display slugs that point here
CANONICAL_TO_ALIASES = {}
for alias_slug, canonical in ALIASES.items():
    CANONICAL_TO_ALIASES.setdefault(canonical, set()).add(alias_slug)


def canonical_slug(name):
    """Return canonical page slug for a wikilink target."""
    slug = normalize_slug(name)
    return ALIASES.get(slug, slug)


def resolve_wikilink(link, all_pages):
    """Check if a wikilink target resolves to any existing page."""
    if canonical_slug(link) in all_pages:
        return True
    return False


def strip_inline_code(text):
    """Remove backtick code spans so [[...]] inside them is ignored."""
    return re.sub(r'`[^`]*`', '', text)


def find_broken_links():
    all_pages = set(normalize_slug(p.stem) for p in VAULT.rglob("*.md"))
    broken = []
    for page in VAULT.rglob("*.md"):
        text = strip_inline_code(page.read_text(encoding="utf-8"))
        for link in re.findall(r'\[\[([^\]]+)\]\]', text):
            if not resolve_wikilink(link, all_pages):
                broken.append((page, link))
    return broken


def find_orphans():
    all_links = set()
    for page in VAULT.rglob("*.md"):
        text = strip_inline_code(page.read_text(encoding="utf-8"))
        for link in re.findall(r'\[\[([^\]]+)\]\]', text):
            slug = canonical_slug(link)
            all_links.add(slug)
            # Also add canonical and all its aliases
            for alias in CANONICAL_TO_ALIASES.get(slug, ()):
                all_links.add(alias)
            all_links.add(slug)

    orphans = []
    exempt = {"index", "log", "lint", "overview", "glossary", "SCHEMA", "OBSIDIAN_SETUP", "Learning-Dashboard"}
    for page in VAULT.rglob("*.md"):
        if normalize_slug(page.stem) not in all_links and page.stem not in exempt:
            orphans.append(page)
    return orphans


def find_stale_pages(days=30):
    stale = []
    now = datetime.now()
    for page in VAULT.rglob("*.md"):
        text = page.read_text(encoding="utf-8")
        updated_match = re.search(r'^updated:\s*(\d{4}-\d{2}-\d{2})', text, re.M)
        if updated_match:
            updated = datetime.strptime(updated_match.group(1), "%Y-%m-%d")
            age = (now - updated).days
            if age > days:
                stale.append((page, age))
    return stale


if __name__ == "__main__":
    print("=== Wiki Lint Report ===\n")

    broken = find_broken_links()
    print(f"Broken links: {len(broken)}")
    for page, link in broken:
        print(f"  {page.relative_to(VAULT)} -> [[{link}]]")

    orphans = find_orphans()
    print(f"\nOrphan pages: {len(orphans)}")
    for page in orphans:
        print(f"  {page.relative_to(VAULT)}")

    stale = find_stale_pages()
    print(f"\nStale pages (>30 days): {len(stale)}")
    for page, age in stale:
        print(f"  {page.relative_to(VAULT)} ({age} days)")

    total = len(broken) + len(orphans) + len(stale)
    if total == 0:
        print("\n✓ Wiki is healthy!")
    else:
        print(f"\n⚠ {total} issues found")
