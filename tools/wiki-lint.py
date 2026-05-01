#!/usr/bin/env python3
"""Weekly wiki health check — broken links, orphans, stale pages."""

from pathlib import Path
import re
from datetime import datetime

VAULT = Path.home() / ".openclaw/workspace/wiki"


def find_broken_links():
    all_pages = set(p.stem for p in VAULT.rglob("*.md"))
    broken = []
    for page in VAULT.rglob("*.md"):
        text = page.read_text(encoding="utf-8")
        for link in re.findall(r'\[\[([^\]]+)\]\]', text):
            # Handle paths like sources/foo or just foo
            slug = link.split('/')[-1] if '/' in link else link
            if slug not in all_pages:
                broken.append((page, link))
    return broken


def find_orphans():
    all_links = set()
    for page in VAULT.rglob("*.md"):
        text = page.read_text(encoding="utf-8")
        for link in re.findall(r'\[\[([^\]]+)\]\]', text):
            slug = link.split('/')[-1] if '/' in link else link
            all_links.add(slug)

    orphans = []
    exempt = {"index", "log", "overview", "glossary", "SCHEMA"}
    for page in VAULT.rglob("*.md"):
        if page.stem not in all_links and page.stem not in exempt:
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
