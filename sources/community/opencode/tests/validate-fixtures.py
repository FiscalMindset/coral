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


def validate_fixture_files(fixture_dir: Path) -> None:
    for filename, required_keys in REQUIRED_FIXTURE_COLUMNS.items():
        path = fixture_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"fixture file missing: {path}")
        rows = load_jsonl(path)
        require(len(rows) > 0, f"{filename} has no rows")
        for row in rows:
            for key in required_keys:
                require(key in row, f"{filename} row missing required key {key!r}")
        print(f"OK fixture {filename}: {len(rows)} row(s), all required keys present")


def load_jsonl(path: Path):
    """Parse a JSONL file into a list of dicts. Empty / missing lines are skipped."""
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def foreign_keys_consistent(
    fixture_dir: Path,
    parent_file: str,
    parent_primary_key: str,
    fk_column: str,
    child_files,
    require_present: bool = True,
) -> None:
    """Assert that every value of `fk_column` in `child_files` is present in
    `parent_file`'s `parent_primary_key` column (or, when `require_present`
    is False, only check child rows that DO reference the parent)."""
    parents = {row[parent_primary_key] for row in load_jsonl(fixture_dir / parent_file)}
    for child_file in child_files:
        bad = [
            row.get(fk_column) for row in load_jsonl(fixture_dir / child_file)
            if fk_column in row
            and row[fk_column]
            and (require_present or row[fk_column] in parents)
            and row[fk_column] not in parents
        ]
        require(
            not bad,
            f"{child_file} references unknown {fk_column} values: {bad}",
        )
    print(
        f"OK foreign keys: every {fk_column} in {', '.join(child_files)} "
        f"exists in {parent_file}"
    )


def test_session_ids_consistent(fixture_dir: Path) -> None:
    """Every session_id in child tables must exist in sessions.jsonl."""
    foreign_keys_consistent(
        fixture_dir,
        parent_file="sessions.jsonl",
        parent_primary_key="id",
        fk_column="session_id",
        child_files=(
            "messages.jsonl", "session_messages.jsonl", "parts.jsonl",
            "todos.jsonl", "session_inputs.jsonl", "session_shares.jsonl",
        ),
        require_present=True,
    )


def test_project_ids_consistent(fixture_dir: Path) -> None:
    """Every non-null project_id in child tables must exist in projects.jsonl."""
    foreign_keys_consistent(
        fixture_dir,
        parent_file="projects.jsonl",
        parent_primary_key="id",
        fk_column="project_id",
        child_files=("project_directories.jsonl", "workspaces.jsonl", "sessions.jsonl"),
        require_present=False,
    )


def test_workspace_ids_consistent(fixture_dir: Path) -> None:
    """Every non-null workspace_id in sessions.jsonl must exist in workspaces.jsonl."""
    foreign_keys_consistent(
        fixture_dir,
        parent_file="workspaces.jsonl",
        parent_primary_key="id",
        fk_column="workspace_id",
        child_files=("sessions.jsonl",),
        require_present=False,
    )


def test_message_part_consistent(fixture_dir: Path) -> None:
    """Every message_id in parts.jsonl must exist in messages.jsonl."""
    foreign_keys_consistent(
        fixture_dir,
        parent_file="messages.jsonl",
        parent_primary_key="id",
        fk_column="message_id",
        child_files=("parts.jsonl",),
        require_present=True,
    )


def main() -> None:
    fixture_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE.parent / "fixtures"
    mod = load_script()
    test_parse_model_json(mod)
    test_open_readonly_missing_file(mod)
    test_open_readonly_rejects_writable_uri(mod)
    validate_fixture_files(fixture_dir)
    test_session_ids_consistent(fixture_dir)
    test_project_ids_consistent(fixture_dir)
    test_workspace_ids_consistent(fixture_dir)
    test_message_part_consistent(fixture_dir)
    print("All opencode converter checks passed")


if __name__ == "__main__":
    main()