#!/usr/bin/env python3
"""
MCP Server for Matt's OpenClaw Wiki Vault
Provides tools for agents to read, write, search, and maintain the wiki.
"""

import json
import sys
import re
from pathlib import Path
from datetime import datetime

VAULT = Path.home() / ".openclaw/workspace"
WIKI = VAULT / "wiki"
RAW = VAULT / "raw"
DB_PATH = VAULT / ".vault-search.db"


def log(msg):
    print(msg, file=sys.stderr)


def list_tools():
    return {
        "tools": [
            {
                "name": "wiki_search",
                "description": "Semantic search over the markdown vault using sqlite-vec",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "k": {"type": "integer", "description": "Number of results", "default": 10}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "wiki_read",
                "description": "Read a wiki page by relative path (e.g. 'concepts/compounding-knowledge')",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Relative path within wiki/"}
                    },
                    "required": ["path"]
                }
            },
            {
                "name": "wiki_write",
                "description": "Write or overwrite a wiki page",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Relative path within wiki/"},
                        "content": {"type": "string", "description": "Full markdown content"}
                    },
                    "required": ["path", "content"]
                }
            },
            {
                "name": "wiki_ingest",
                "description": "Ingest a raw source file into the wiki",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "source_path": {"type": "string", "description": "Absolute or relative path to source file"}
                    },
                    "required": ["source_path"]
                }
            },
            {
                "name": "wiki_lint",
                "description": "Run wiki health check — broken links, orphans, stale pages",
                "inputSchema": {"type": "object", "properties": {}}
            },
            {
                "name": "wiki_index",
                "description": "Reindex the vault for semantic search",
                "inputSchema": {"type": "object", "properties": {}}
            },
            {
                "name": "wiki_log_append",
                "description": "Append an entry to wiki/log.md",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "entry": {"type": "string", "description": "Log entry text (markdown)"}
                    },
                    "required": ["entry"]
                }
            }
        ]
    }


def wiki_search(query, k=10):
    import sqlite3
    import sqlite_vec
    try:
        db = sqlite3.connect(DB_PATH)
        db.enable_load_extension(True)
        sqlite_vec.load(db)
        from model2vec import StaticModel
        model = StaticModel.from_pretrained("minishlab/potion-base-8M")
        query_vec = model.encode(query)
        results = db.execute("""
            SELECT docs.path, contents.title, contents.tags, distance
            FROM docs
            JOIN contents ON docs.path = contents.path
            WHERE embedding MATCH ? AND k = ?
            ORDER BY distance
        """, (sqlite_vec.serialize_float32(query_vec), k))
        rows = results.fetchall()
        return {
            "content": [{"type": "text", "text": json.dumps([{
                "path": str(Path(r[0]).relative_to(VAULT)),
                "title": r[1],
                "tags": r[2],
                "distance": r[3]
            } for r in rows])}]
        }
    except Exception as e:
        return {"content": [{"type": "text", "text": f"Search error: {e}"}], "isError": True}


def wiki_read(path):
    target = WIKI / path
    if not target.exists():
        return {"content": [{"type": "text", "text": f"Page not found: {path}"}], "isError": True}
    return {"content": [{"type": "text", "text": target.read_text()}]}


def wiki_write(path, content):
    target = WIKI / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)
    return {"content": [{"type": "text", "text": f"Written: {target}"}]}


def wiki_ingest(source_path):
    import subprocess
    result = subprocess.run(
        [sys.executable, str(VAULT / "tools/mcp-wiki-ingest.py"), source_path],
        capture_output=True, text=True
    )
    return {"content": [{"type": "text", "text": result.stdout or result.stderr}]}


def wiki_lint():
    import subprocess
    result = subprocess.run(
        [sys.executable, str(VAULT / "tools/wiki-lint.py")],
        capture_output=True, text=True
    )
    return {"content": [{"type": "text", "text": result.stdout or result.stderr}]}


def wiki_index():
    import subprocess
    result = subprocess.run(
        [sys.executable, str(VAULT / "tools/search-vault.py"), "index"],
        capture_output=True, text=True
    )
    return {"content": [{"type": "text", "text": result.stdout or result.stderr}]}


def wiki_log_append(entry):
    log_file = WIKI / "log.md"
    today = datetime.now().strftime("%Y-%m-%d")
    if log_file.exists():
        content = log_file.read_text()
    else:
        content = "# Wiki Log\n\n"
    content += f"\n## [{today}] auto | {entry}\n"
    log_file.write_text(content)
    return {"content": [{"type": "text", "text": "Log appended."}]}


def handle_request(req):
    method = req.get("method")
    if method == "initialize":
        return {"jsonrpc": "2.0", "id": req.get("id"), "result": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "serverInfo": {"name": "openclaw-wiki-mcp", "version": "0.1.0"}
        }}
    elif method == "tools/list":
        return {"jsonrpc": "2.0", "id": req.get("id"), "result": list_tools()}
    elif method == "tools/call":
        params = req.get("params", {})
        name = params.get("name")
        args = params.get("arguments", {})
        if name == "wiki_search":
            result = wiki_search(args.get("query"), args.get("k", 10))
        elif name == "wiki_read":
            result = wiki_read(args.get("path"))
        elif name == "wiki_write":
            result = wiki_write(args.get("path"), args.get("content"))
        elif name == "wiki_ingest":
            result = wiki_ingest(args.get("source_path"))
        elif name == "wiki_lint":
            result = wiki_lint()
        elif name == "wiki_index":
            result = wiki_index()
        elif name == "wiki_log_append":
            result = wiki_log_append(args.get("entry"))
        else:
            result = {"content": [{"type": "text", "text": f"Unknown tool: {name}"}], "isError": True}
        return {"jsonrpc": "2.0", "id": req.get("id"), "result": result}
    else:
        return {"jsonrpc": "2.0", "id": req.get("id"), "error": {"code": -32601, "message": f"Method not found: {method}"}}


def main():
    log("OpenClaw Wiki MCP Server starting...")
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            resp = handle_request(req)
            print(json.dumps(resp), flush=True)
        except json.JSONDecodeError as e:
            log(f"JSON parse error: {e}")
            print(json.dumps({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}), flush=True)


if __name__ == "__main__":
    main()
