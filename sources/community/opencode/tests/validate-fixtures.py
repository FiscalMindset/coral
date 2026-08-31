#!/usr/bin/env python3
"""Regression tests for the opencode converter script and fixtures.

Covers the parser and JSON-column helpers that needed correctness fixes
during review, plus fixture-shape sanity checks, per the source
contribution testing expectations in CONTRIBUTING.md.
"""

import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE_DIR = HERE.parent
SCRIPT_PATH = SOURCE_DIR / "scripts" / "opencode-to-jsonl.py"


def load_script():
    spec = importlib.util.spec_from_file_location("opencode_to_jsonl", SCRIPT_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def test_parse_model_json(mod) -> None:
    """OpenCode stores `model` as a JSON string `{"id":..,"providerID":..,"variant":..}`."""
    require(
        mod.parse_model('{"id":"x","providerID":"y","variant":"default"}') == ("y", "x"),
        "provider id should come from providerID, model id from id",
    )
    require(
        mod.parse_model('{"id":"MiniMax-M3","providerID":"samagama"}') == ("samagama", "MiniMax-M3"),
        "missing variant should still split correctly",
    )
    require(mod.parse_model("") == (None, None), "empty string should return None, None")
    require(mod.parse_model(None) == (None, None), "None should return None, None")
    require(mod.parse_model("plain-model-id") == (None, None),
           "non-JSON string should return None, None (do not guess)")
    require(mod.parse_model('{"foo":"bar"}') == (None, None),
           "JSON without id/providerID should return None, None")
    require(mod.parse_model('[1,2,3]') == (None, None),
           "non-object JSON should return None, None")
    print("OK parse_model: JSON object, missing keys, non-JSON, None")


def test_open_readonly_missing_file(mod) -> None:
    require(
        not Path("/tmp/definitely-does-not-exist-opencode-12345.db").exists(),
        "test precondition",
    )
    try:
        mod.open_readonly(Path("/tmp/definitely-does-not-exist-opencode-12345.db"))
    except FileNotFoundError as exc:
        require(
            "OpenCode database not found" in str(exc),
            f"missing-file error should mention OpenCode database not found, got {exc!r}",
        )
        print("OK open_readonly: clear error when the database is missing")
        return
    raise AssertionError("open_readonly should have raised FileNotFoundError")


def test_open_readonly_rejects_writable_uri(mod) -> None:
    """`mode=ro` must reject any write attempt at the SQLite level."""
    import sqlite3
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        tmp_path = Path(f.name)
    try:
        writable = sqlite3.connect(tmp_path)
        writable.execute("CREATE TABLE t (n INTEGER)")
        writable.execute("INSERT INTO t VALUES (1)")
        writable.commit()
        writable.close()

        ro = mod.open_readonly(tmp_path)
        try:
            try:
                ro.execute("INSERT INTO t VALUES (2)")
                ro.commit()
            except sqlite3.OperationalError:
                pass
            else:
                raise AssertionError(
                    "open_readonly should reject writes (mode=ro is enforced)"
                )
            print("OK open_readonly: write attempts are rejected (read-only enforced)")
        finally:
            ro.close()
    finally:
        tmp_path.unlink(missing_ok=True)


REQUIRED_FIXTURE_COLUMNS = {
    "sessions.jsonl": [
        "id", "title", "agent", "model", "model_id", "model_provider",
        "tokens_input", "tokens_output", "cost",
        "time_created", "time_updated",
    ],
    "messages.jsonl": ["id", "session_id", "time_created", "data"],
    "session_messages.jsonl": ["id", "session_id", "type", "seq", "data"],
    "parts.jsonl": ["id", "message_id", "session_id", "data"],
    "todos.jsonl": ["session_id", "content", "status", "position"],
    "session_inputs.jsonl": ["id", "session_id", "prompt", "admitted_seq"],
    "session_shares.jsonl": ["session_id", "id", "url"],
    "projects.jsonl": ["id", "worktree", "time_created", "time_updated"],
    "project_directories.jsonl": ["project_id", "directory", "time_created"],
    "workspaces.jsonl": ["id", "project_id", "type", "time_used"],
}


def validate_fixture_files() -> None:
    fixture_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE.parent / "fixtures"
    for filename, required_keys in REQUIRED_FIXTURE_COLUMNS.items():
        path = fixture_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"fixture file missing: {path}")
        rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        require(len(rows) > 0, f"{filename} has no rows")
        for row in rows:
            for key in required_keys:
                require(key in row, f"{filename} row missing required key {key!r}")
        print(f"OK fixture {filename}: {len(rows)} row(s), all required keys present")


def test_session_ids_consistent() -> None:
    """Spot-check that fixture session ids referenced by child tables exist in sessions.jsonl."""
    fixture_dir = HERE.parent / "fixtures"
    sessions = {json.loads(line)["id"] for line in
                (fixture_dir / "sessions.jsonl").read_text().splitlines() if line.strip()}
    for child in ("messages.jsonl", "session_messages.jsonl", "parts.jsonl",
                  "todos.jsonl", "session_inputs.jsonl", "session_shares.jsonl"):
        rows = [json.loads(line) for line in
                (fixture_dir / child).read_text().splitlines() if line.strip()]
        bad = [r.get("session_id") for r in rows
               if "session_id" in r and r["session_id"] not in sessions]
        require(
            not bad,
            f"{child} references unknown session_ids: {bad}",
        )
    print("OK foreign keys: every session_id in child tables exists in sessions.jsonl")


def test_project_ids_consistent() -> None:
    fixture_dir = HERE.parent / "fixtures"
    projects = {json.loads(line)["id"] for line in
                (fixture_dir / "projects.jsonl").read_text().splitlines() if line.strip()}
    for child in ("project_directories.jsonl", "workspaces.jsonl", "sessions.jsonl"):
        rows = [json.loads(line) for line in
                (fixture_dir / child).read_text().splitlines() if line.strip()]
        bad = [r.get("project_id") for r in rows
               if "project_id" in r and r["project_id"] and r["project_id"] not in projects]
        require(not bad, f"{child} references unknown project_ids: {bad}")
    print("OK foreign keys: every project_id in child tables exists in projects.jsonl")


def test_message_part_consistent() -> None:
    fixture_dir = HERE.parent / "fixtures"
    messages = {json.loads(line)["id"] for line in
                (fixture_dir / "messages.jsonl").read_text().splitlines() if line.strip()}
    rows = [json.loads(line) for line in
            (fixture_dir / "parts.jsonl").read_text().splitlines() if line.strip()]
    bad = [r["message_id"] for r in rows if r["message_id"] not in messages]
    require(not bad, f"parts references unknown message_ids: {bad}")
    print("OK foreign keys: every message_id in parts exists in messages.jsonl")


def main() -> None:
    mod = load_script()
    test_parse_model_json(mod)
    test_open_readonly_missing_file(mod)
    test_open_readonly_rejects_writable_uri(mod)
    validate_fixture_files()
    test_session_ids_consistent()
    test_project_ids_consistent()
    test_message_part_consistent()
    print("All opencode converter checks passed")


if __name__ == "__main__":
    main()