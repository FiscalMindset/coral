#!/usr/bin/env python3
"""Fetch Google Sheets data and write JSONL for the Coral google_sheets source.

Uses only Python stdlib (urllib). No external dependencies.

Usage:
    python3 sheets-to-jsonl.py --api-key YOUR_KEY --spreadsheet-id SHEET_ID
    python3 sheets-to-jsonl.py --api-key YOUR_KEY --spreadsheet-id SHEET_ID --sheet "App_Master"
    python3 sheets-to-jsonl.py --api-key YOUR_KEY --spreadsheet-id SHEET_ID --output ~/.coral/google_sheets

Output:
    rows.jsonl   — one row per data row with column headers as keys
    sheets.jsonl — one row per sheet tab with metadata
"""

import argparse
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

DEFAULT_OUTPUT = os.path.expanduser("~/.coral/google_sheets")
API_BASE = "https://sheets.googleapis.com/v4/spreadsheets"


def fetch_json(url):
    try:
        req = Request(url)
        resp = urlopen(req, timeout=30)
        return json.loads(resp.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            err = json.loads(body)
            msg = err.get("error", {}).get("message", body)
        except (json.JSONDecodeError, KeyError):
            msg = body
        print(f"  ✗ API error ({exc.code}): {msg}", file=sys.stderr)
        return None
    except URLError as exc:
        print(f"  ✗ Connection error: {exc.reason}", file=sys.stderr)
        return None


def fetch_metadata(spreadsheet_id, api_key):
    url = (
        f"{API_BASE}/{quote(spreadsheet_id)}"
        f"?key={api_key}"
        f"&fields=spreadsheetId,properties.title,sheets.properties"
    )
    return fetch_json(url)


def fetch_values(spreadsheet_id, sheet_name, api_key):
    url = (
        f"{API_BASE}/{quote(spreadsheet_id)}"
        f"/values/{quote(sheet_name)}"
        f"?key={api_key}"
    )
    return fetch_json(url)


def main():
    parser = argparse.ArgumentParser(
        description="Fetch Google Sheets data to JSONL for Coral"
    )
    parser.add_argument(
        "--api-key", required=True,
        help="Google Sheets API key",
    )
    parser.add_argument(
        "--spreadsheet-id", required=True,
        help="Google Spreadsheet ID from the URL",
    )
    parser.add_argument(
        "--sheet", default=None,
        help="Specific sheet tab name (default: all sheets)",
    )
    parser.add_argument(
        "--output", "-o", default=DEFAULT_OUTPUT,
        help=f"Output directory (default: {DEFAULT_OUTPUT})",
    )
    args = parser.parse_args()

    print(f"  Fetching metadata for {args.spreadsheet_id}...")
    meta = fetch_metadata(args.spreadsheet_id, args.api_key)
    if meta is None:
        sys.exit(1)

    title = meta.get("properties", {}).get("title", "untitled")
    all_sheets = meta.get("sheets", [])
    print(f"  Spreadsheet: {title} ({len(all_sheets)} sheets)")

    if args.sheet:
        target_sheets = [
            s for s in all_sheets
            if s["properties"]["title"] == args.sheet
        ]
        if not target_sheets:
            names = [s["properties"]["title"] for s in all_sheets]
            print(
                f"  ✗ Sheet '{args.sheet}' not found. Available: {names}",
                file=sys.stderr,
            )
            sys.exit(1)
    else:
        target_sheets = all_sheets

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    rows_path = output_dir / "rows.jsonl"
    sheets_path = output_dir / "sheets.jsonl"

    tmp_rows = tempfile.NamedTemporaryFile(
        mode="w", dir=output_dir, suffix=".jsonl", delete=False,
    )
    tmp_sheets = tempfile.NamedTemporaryFile(
        mode="w", dir=output_dir, suffix=".jsonl", delete=False,
    )

    total_rows = 0
    fail_count = 0

    try:
        for sheet_info in target_sheets:
            props = sheet_info["properties"]
            sheet_name = props["title"]
            grid = props.get("gridProperties", {})

            sheet_meta = {
                "spreadsheet_id": args.spreadsheet_id,
                "spreadsheet_title": title,
                "sheet_name": sheet_name,
                "sheet_id": props.get("sheetId"),
                "sheet_type": props.get("sheetType", "GRID"),
                "row_count": grid.get("rowCount"),
                "column_count": grid.get("columnCount"),
            }
            tmp_sheets.write(json.dumps(sheet_meta) + "\n")

            print(f"  → {sheet_name}")
            data = fetch_values(args.spreadsheet_id, sheet_name, args.api_key)
            if data is None:
                fail_count += 1
                continue

            values = data.get("values", [])
            if len(values) < 2:
                print(f"    (empty or header-only, skipping)")
                continue

            headers = values[0]
            for row_idx, row_values in enumerate(values[1:], start=1):
                data = {}
                for i, header in enumerate(headers):
                    key = header.strip() if header else f"col_{i}"
                    data[key] = row_values[i] if i < len(row_values) else None
                row = {
                    "_spreadsheet_id": args.spreadsheet_id,
                    "_sheet_name": sheet_name,
                    "_row_number": row_idx,
                    "data": data,
                }
                tmp_rows.write(json.dumps(row) + "\n")
                total_rows += 1

        tmp_rows.close()
        tmp_sheets.close()

        if fail_count > 0:
            os.unlink(tmp_rows.name)
            os.unlink(tmp_sheets.name)
            print(f"\n  ✗ {fail_count} sheets failed — existing files preserved",
                  file=sys.stderr)
            sys.exit(1)

        shutil.move(tmp_rows.name, rows_path)
        shutil.move(tmp_sheets.name, sheets_path)

    except BaseException:
        tmp_rows.close()
        tmp_sheets.close()
        for f in [tmp_rows.name, tmp_sheets.name]:
            if os.path.exists(f):
                os.unlink(f)
        raise

    print(f"\n  ✓ {total_rows} rows → {rows_path}")
    print(f"  ✓ {len(target_sheets)} sheets → {sheets_path}")


if __name__ == "__main__":
    main()
