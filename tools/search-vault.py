#!/usr/bin/env python3
"""Hybrid search over the markdown vault using sqlite-vec + model2vec."""

import sqlite_vec
import sqlite3
import json
import os
import re
import sys
from pathlib import Path

# Path configuration
VAULT_PATH = Path.home() / ".openclaw/workspace"
DB_PATH = VAULT_PATH / ".vault-search.db"

# We import model2vec lazily to avoid slow startup on simple commands
def get_model():
    from model2vec import StaticModel
    return StaticModel.from_pretrained("minishlab/potion-base-8M")


def init_db():
    db = sqlite3.connect(DB_PATH)
    db.enable_load_extension(True)
    sqlite_vec.load(db)
    db.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS docs USING vec0(
            path TEXT PRIMARY KEY,
            embedding FLOAT[256] distance_metric=cosine
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS contents (
            path TEXT PRIMARY KEY,
            title TEXT,
            body TEXT,
            tags TEXT
        )
    """)
    return db


def index_vault():
    model = get_model()
    db = init_db()
    count = 0

    for md_file in VAULT_PATH.rglob("*.md"):
        if ".git" in str(md_file):
            continue
        text = md_file.read_text(encoding="utf-8")

        # Extract frontmatter title
        title_match = re.search(r'^title:\s*"?([^"\n]+)"?', text, re.M)
        title = title_match.group(1) if title_match else md_file.stem

        # Extract tags
        tags = re.findall(r'#(\w+[-\w+]*)', text)

        # Get embedding of full text
        embedding = model.encode(text)

        db.execute(
            "INSERT OR REPLACE INTO docs VALUES (?, ?)",
            (str(md_file), sqlite_vec.serialize_float32(embedding))
        )
        db.execute(
            "INSERT OR REPLACE INTO contents VALUES (?, ?, ?, ?)",
            (str(md_file), title, text, json.dumps(tags))
        )
        count += 1

    db.commit()
    print(f"Indexed {count} documents")


def search(query, k=10):
    model = get_model()
    db = init_db()
    query_vec = model.encode(query)

    results = db.execute("""
        SELECT docs.path, contents.title, contents.tags, distance
        FROM docs
        JOIN contents ON docs.path = contents.path
        WHERE embedding MATCH ? AND k = ?
        ORDER BY distance
    """, (sqlite_vec.serialize_float32(query_vec), k))

    return results.fetchall()


def main():
    if len(sys.argv) < 2:
        print("Usage: search-vault.py [index | search <query> | grep <keyword>]")
        sys.exit(1)

    command = sys.argv[1]

    if command == "index":
        index_vault()

    elif command == "search":
        query = " ".join(sys.argv[2:])
        if not query:
            print("Usage: search-vault.py search <query>")
            sys.exit(1)
        results = search(query)
        if not results:
            print("No results found.")
            return
        for path, title, tags, dist in results:
            rel = Path(path).relative_to(VAULT_PATH)
            tag_str = ", ".join(json.loads(tags)) if tags else ""
            print(f"{dist:.3f} | {title} | {rel} | {tag_str}")

    elif command == "grep":
        keyword = sys.argv[2] if len(sys.argv) > 2 else ""
        if not keyword:
            print("Usage: search-vault.py grep <keyword>")
            sys.exit(1)
        for md_file in VAULT_PATH.rglob("*.md"):
            if ".git" in str(md_file):
                continue
            text = md_file.read_text(encoding="utf-8")
            if keyword.lower() in text.lower():
                rel = md_file.relative_to(VAULT_PATH)
                # Extract title
                title_match = re.search(r'^title:\s*"?([^"\n]+)"?', text, re.M)
                title = title_match.group(1) if title_match else md_file.stem
                print(f"[match] {title} | {rel}")

    else:
        print(f"Unknown command: {command}")
        print("Usage: search-vault.py [index | search <query> | grep <keyword>]")
        sys.exit(1)


if __name__ == "__main__":
    main()
