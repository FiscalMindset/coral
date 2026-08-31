#!/usr/bin/env python3
"""Export OpenCode session, message, and project data to JSONL for Coral.

Uses only Python stdlib (sqlite3). No external dependencies.

Usage:
    python3 opencode-to-jsonl.py
    python3 opencode-to-jsonl.py --db-path /path/to/opencode.db
    python3 opencode-to-jsonl.py --db-path /path/to/opencode.db --output /path/to/dir

OpenCode stores its data in a local SQLite database. By default the script
reads `~/.local/share/opencode/opencode.db` and writes:

    sessions.jsonl          — one row per session with flattened columns
                              and a metadata JSON blob for the raw
                              JSON-shaped fields
    messages.jsonl          — one row per message with id, session id,
                              timestamps, and the full payload as JSON
    session_messages.jsonl  — one row per session_message (alternative
                              message table indexed by session sequence)
    parts.jsonl             — one row per message part (text, tool calls,
                              images, etc.) — the actual transcript content
    todos.jsonl             — one row per session todo list entry
    session_inputs.jsonl    — one row per user prompt admitted to a session
    session_shares.jsonl    — one row per shared session URL
    projects.jsonl          — one row per project with id, worktree, name,
                              and timestamps
    project_directories.jsonl — one row per directory attached to a project
    workspaces.jsonl        — one row per workspace

Default output directory: `~/.coral/opencode/`.

The script reads the database in a read-only connection (`mode=ro`) so it
never touches OpenCode's live state. Re-run any time the on-disk database
changes to refresh Coral's view.
"""

import argparse
import json
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

DEFAULT_DB_PATH = os.path.expanduser("~/.local/share/opencode/opencode.db")
DEFAULT_OUTPUT = os.path.expanduser("~/.coral/opencode")


def open_readonly(db_path: Path) -> sqlite3.Connection:
    """Open the SQLite database in read-only mode."""
    if not db_path.is_file():
        raise FileNotFoundError(
            f"OpenCode database not found: {db_path}\n"
            f"  - Is OpenCode installed and has run at least once?\n"
            f"  - Or pass --db-path to point at a non-default location."
        )
    uri = f"file:{db_path}?mode=ro"
    return sqlite3.connect(uri, uri=True)


def parse_model(model: str):
    """Split OpenCode's JSON-encoded model column into (provider, model_id).

    OpenCode stores the model as a JSON object shaped
    `{"id":"MiniMax-M3","providerID":"samagama","variant":"default"}`.
    Anything we cannot parse is returned as (None, None) so the caller can
    fall back to the raw value rather than guess.
    """
    if not model:
        return None, None
    try:
        obj = json.loads(model)
    except (TypeError, ValueError):
        return None, None
    if not isinstance(obj, dict):
        return None, None
    provider = obj.get("providerID") or None
    model_id = obj.get("id") or None
    return provider, model_id


def fetch_sessions(conn: sqlite3.Connection):
    sql = """
        SELECT id, project_id, parent_id, workspace_id, slug, title, directory,
               path, agent, model, version, share_url,
               tokens_input, tokens_output, tokens_reasoning,
               tokens_cache_read, tokens_cache_write, cost,
               time_created, time_updated, time_compacting, time_archived,
               metadata, summary_diffs, revert, permission
        FROM session
        ORDER BY time_updated DESC, id ASC
    """
    rows = []
    for r in conn.execute(sql):
        model_provider, model_id = parse_model(r["model"] or "")
        metadata_blob = {}
        for field, key in (
            ("metadata", "metadata"),
            ("summary_diffs", "summary_diffs"),
            ("revert", "revert"),
            ("permission", "permission"),
        ):
            raw = r[field]
            if raw is None or raw == "":
                continue
            try:
                metadata_blob[key] = json.loads(raw)
            except (TypeError, ValueError):
                metadata_blob[key] = raw
        rows.append(
            {
                "id": r["id"],
                "project_id": r["project_id"],
                "parent_id": r["parent_id"],
                "workspace_id": r["workspace_id"],
                "slug": r["slug"],
                "title": r["title"],
                "directory": r["directory"],
                "path": r["path"],
                "agent": r["agent"],
                "model": r["model"],
                "model_id": model_id,
                "model_provider": model_provider,
                "version": r["version"],
                "share_url": r["share_url"],
                "tokens_input": int(r["tokens_input"] or 0),
                "tokens_output": int(r["tokens_output"] or 0),
                "tokens_reasoning": int(r["tokens_reasoning"] or 0),
                "tokens_cache_read": int(r["tokens_cache_read"] or 0),
                "tokens_cache_write": int(r["tokens_cache_write"] or 0),
                "cost": float(r["cost"] or 0.0),
                "time_created": int(r["time_created"] or 0),
                "time_updated": int(r["time_updated"] or 0),
                "time_compacting": int(r["time_compacting"]) if r["time_compacting"] is not None else None,
                "time_archived": int(r["time_archived"]) if r["time_archived"] is not None else None,
                "metadata": metadata_blob or None,
            }
        )
    return rows


def fetch_messages(conn: sqlite3.Connection):
    sql = """
        SELECT id, session_id, time_created, time_updated, data
        FROM message
        ORDER BY session_id ASC, time_created ASC, id ASC
    """
    rows = []
    for r in conn.execute(sql):
        raw = r["data"]
        try:
            payload = json.loads(raw) if raw else {}
        except (TypeError, ValueError):
            payload = {"_raw": raw}
        rows.append(
            {
                "id": r["id"],
                "session_id": r["session_id"],
                "time_created": int(r["time_created"] or 0),
                "time_updated": int(r["time_updated"] or 0),
                "data": payload,
            }
        )
    return rows


def fetch_projects(conn: sqlite3.Connection):
    sql = """
        SELECT id, worktree, vcs, name, icon_url, icon_url_override,
               icon_color, time_created, time_updated, time_initialized
        FROM project
        ORDER BY time_created DESC, id ASC
    """
    rows = []
    for r in conn.execute(sql):
        rows.append(
            {
                "id": r["id"],
                "worktree": r["worktree"],
                "vcs": r["vcs"],
                "name": r["name"],
                "icon_url": r["icon_url_override"] or r["icon_url"],
                "icon_color": r["icon_color"],
                "time_created": int(r["time_created"] or 0),
                "time_updated": int(r["time_updated"] or 0),
                "time_initialized": int(r["time_initialized"]) if r["time_initialized"] is not None else None,
            }
        )
    return rows


def fetch_project_directories(conn: sqlite3.Connection):
    sql = """
        SELECT project_id, directory, type, strategy, time_created
        FROM project_directory
        ORDER BY project_id ASC, directory ASC
    """
    rows = []
    for r in conn.execute(sql):
        rows.append(
            {
                "project_id": r["project_id"],
                "directory": r["directory"],
                "type": r["type"],
                "strategy": r["strategy"],
                "time_created": int(r["time_created"] or 0),
            }
        )
    return rows


def fetch_parts(conn: sqlite3.Connection):
    sql = """
        SELECT id, message_id, session_id, time_created, time_updated, data
        FROM part
        ORDER BY session_id ASC, time_created ASC, id ASC
    """
    rows = []
    for r in conn.execute(sql):
        raw = r["data"]
        try:
            payload = json.loads(raw) if raw else {}
        except (TypeError, ValueError):
            payload = {"_raw": raw}
        rows.append(
            {
                "id": r["id"],
                "message_id": r["message_id"],
                "session_id": r["session_id"],
                "time_created": int(r["time_created"] or 0),
                "time_updated": int(r["time_updated"] or 0),
                "data": payload,
            }
        )
    return rows


def fetch_todos(conn: sqlite3.Connection):
    sql = """
        SELECT session_id, content, status, priority, position,
               time_created, time_updated
        FROM todo
        ORDER BY session_id ASC, position ASC
    """
    rows = []
    for r in conn.execute(sql):
        rows.append(
            {
                "session_id": r["session_id"],
                "content": r["content"],
                "status": r["status"],
                "priority": r["priority"],
                "position": int(r["position"] or 0),
                "time_created": int(r["time_created"] or 0),
                "time_updated": int(r["time_updated"] or 0),
            }
        )
    return rows


def fetch_session_inputs(conn: sqlite3.Connection):
    sql = """
        SELECT id, session_id, prompt, delivery, admitted_seq, promoted_seq,
               time_created
        FROM session_input
        ORDER BY session_id ASC, admitted_seq ASC
    """
    rows = []
    for r in conn.execute(sql):
        rows.append(
            {
                "id": r["id"],
                "session_id": r["session_id"],
                "prompt": r["prompt"],
                "delivery": r["delivery"],
                "admitted_seq": int(r["admitted_seq"] or 0),
                "promoted_seq": int(r["promoted_seq"]) if r["promoted_seq"] is not None else None,
                "time_created": int(r["time_created"] or 0),
            }
        )
    return rows


def fetch_session_messages(conn: sqlite3.Connection):
    sql = """
        SELECT id, session_id, type, seq, time_created, time_updated, data
        FROM session_message
        ORDER BY session_id ASC, seq ASC
    """
    rows = []
    for r in conn.execute(sql):
        raw = r["data"]
        try:
            payload = json.loads(raw) if raw else {}
        except (TypeError, ValueError):
            payload = {"_raw": raw}
        rows.append(
            {
                "id": r["id"],
                "session_id": r["session_id"],
                "type": r["type"],
                "seq": int(r["seq"] or 0),
                "time_created": int(r["time_created"] or 0),
                "time_updated": int(r["time_updated"] or 0),
                "data": payload,
            }
        )
    return rows


def fetch_session_shares(conn: sqlite3.Connection):
    sql = """
        SELECT session_id, id, secret, url, time_created, time_updated
        FROM session_share
        ORDER BY time_created DESC, session_id ASC
    """
    rows = []
    for r in conn.execute(sql):
        rows.append(
            {
                "session_id": r["session_id"],
                "id": r["id"],
                "secret": r["secret"],
                "url": r["url"],
                "time_created": int(r["time_created"] or 0),
                "time_updated": int(r["time_updated"] or 0),
            }
        )
    return rows


def fetch_workspaces(conn: sqlite3.Connection):
    sql = """
        SELECT id, project_id, directory, type, name, branch, extra, time_used
        FROM workspace
        ORDER BY project_id ASC, directory ASC
    """
    rows = []
    for r in conn.execute(sql):
        rows.append(
            {
                "id": r["id"],
                "project_id": r["project_id"],
                "directory": r["directory"],
                "type": r["type"],
                "name": r["name"],
                "branch": r["branch"],
                "extra": r["extra"],
                "time_used": int(r["time_used"] or 0),
            }
        )
    return rows


def write_jsonl_atomic(path: Path, rows):
    """Write `rows` to `path` as JSONL atomically via a temp file in the same dir."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = tempfile.NamedTemporaryFile(
        mode="w", dir=str(path.parent), suffix=".jsonl", delete=False, encoding="utf-8"
    )
    try:
        for row in rows:
            tmp.write(json.dumps(row, separators=(",", ":")) + "\n")
        tmp.close()
        os.replace(tmp.name, path)
    except BaseException:
        tmp.close()
        if os.path.exists(tmp.name):
            os.unlink(tmp.name)
        raise


def main():
    parser = argparse.ArgumentParser(
        description="Export OpenCode session data to JSONL for Coral"
    )
    parser.add_argument(
        "--db-path",
        default=DEFAULT_DB_PATH,
        help=f"Path to the OpenCode SQLite database (default: {DEFAULT_DB_PATH})",
    )
    parser.add_argument(
        "--output", "-o",
        default=DEFAULT_OUTPUT,
        help=f"Output directory (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--only",
        choices=(
            "sessions", "messages", "session_messages", "parts", "todos",
            "session_inputs", "session_shares", "projects",
            "project_directories", "workspaces",
        ),
        default=None,
        help="Export only one table (default: export all).",
    )
    args = parser.parse_args()

    db_path = Path(args.db_path)
    output_dir = Path(args.output)

    conn = open_readonly(db_path)
    conn.row_factory = sqlite3.Row
    try:
        if args.only in (None, "sessions"):
            sessions = fetch_sessions(conn)
            write_jsonl_atomic(output_dir / "sessions.jsonl", sessions)
            print(f"  ✓ {len(sessions):>6} sessions    → {output_dir / 'sessions.jsonl'}")
        if args.only in (None, "messages"):
            messages = fetch_messages(conn)
            write_jsonl_atomic(output_dir / "messages.jsonl", messages)
            print(f"  ✓ {len(messages):>6} messages    → {output_dir / 'messages.jsonl'}")
        if args.only in (None, "session_messages"):
            sm = fetch_session_messages(conn)
            write_jsonl_atomic(output_dir / "session_messages.jsonl", sm)
            print(f"  ✓ {len(sm):>6} session_messages → {output_dir / 'session_messages.jsonl'}")
        if args.only in (None, "parts"):
            parts = fetch_parts(conn)
            write_jsonl_atomic(output_dir / "parts.jsonl", parts)
            print(f"  ✓ {len(parts):>6} parts       → {output_dir / 'parts.jsonl'}")
        if args.only in (None, "todos"):
            todos = fetch_todos(conn)
            write_jsonl_atomic(output_dir / "todos.jsonl", todos)
            print(f"  ✓ {len(todos):>6} todos       → {output_dir / 'todos.jsonl'}")
        if args.only in (None, "session_inputs"):
            si = fetch_session_inputs(conn)
            write_jsonl_atomic(output_dir / "session_inputs.jsonl", si)
            print(f"  ✓ {len(si):>6} session_inputs → {output_dir / 'session_inputs.jsonl'}")
        if args.only in (None, "session_shares"):
            ss = fetch_session_shares(conn)
            write_jsonl_atomic(output_dir / "session_shares.jsonl", ss)
            print(f"  ✓ {len(ss):>6} session_shares → {output_dir / 'session_shares.jsonl'}")
        if args.only in (None, "projects"):
            projects = fetch_projects(conn)
            write_jsonl_atomic(output_dir / "projects.jsonl", projects)
            print(f"  ✓ {len(projects):>6} projects    → {output_dir / 'projects.jsonl'}")
        if args.only in (None, "project_directories"):
            pd = fetch_project_directories(conn)
            write_jsonl_atomic(output_dir / "project_directories.jsonl", pd)
            print(f"  ✓ {len(pd):>6} project_directories → {output_dir / 'project_directories.jsonl'}")
        if args.only in (None, "workspaces"):
            ws = fetch_workspaces(conn)
            write_jsonl_atomic(output_dir / "workspaces.jsonl", ws)
            print(f"  ✓ {len(ws):>6} workspaces  → {output_dir / 'workspaces.jsonl'}")
    finally:
        conn.close()

    print(f"\n  OpenCode data exported from {db_path}")
    print(f"  Next: coral source add --file sources/community/opencode/manifest.yaml")


if __name__ == "__main__":
    main()
