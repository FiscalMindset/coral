# Google Sheets

**Version:** 0.1.0
**Backend:** File (JSONL)
**Tables:** 2

Query Google Sheets data from local JSONL files. Extract spreadsheet rows with proper column headers and sheet metadata through SQL.

## Installation

1. Run the converter script to fetch spreadsheet data:

```bash
python3 sources/community/google_sheets/scripts/sheets-to-jsonl.py \
  --api-key YOUR_GOOGLE_API_KEY \
  --spreadsheet-id YOUR_SPREADSHEET_ID
```

2. Install the source:

```bash
coral source add --file sources/community/google_sheets/manifest.yaml
```

## Prerequisites

- Python 3.8+ (no external dependencies — uses only stdlib)
- Google Sheets API key from [Google Cloud Console](https://console.cloud.google.com)
- Spreadsheet must be shared as **"Anyone with the link"** (public read access)

**Getting an API key:**
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create or select a project
3. Enable the **Google Sheets API**
4. Go to **Credentials** > **Create Credentials** > **API Key**
5. Copy the key

## Quick Start

```sql
-- List all rows with full data
SELECT _sheet_name, _row_number, data
FROM google_sheets.rows
LIMIT 10;

-- Extract specific fields from the data column
SELECT
  json_as_text(data, 'app') AS app,
  json_as_text(data, 'subcategory_id') AS category,
  json_as_text(data, 'availability') AS availability
FROM google_sheets.rows
LIMIT 10;

-- Filter by sheet name
SELECT _row_number, data
FROM google_sheets.rows
WHERE _sheet_name = 'App_Master'
LIMIT 10;

-- View sheet metadata
SELECT spreadsheet_title, sheet_name, row_count, column_count
FROM google_sheets.sheets;
```

## Converter Usage

```bash
# Fetch all sheets from a spreadsheet
python3 sources/community/google_sheets/scripts/sheets-to-jsonl.py \
  --api-key YOUR_KEY --spreadsheet-id SHEET_ID

# Fetch a specific sheet tab only
python3 sources/community/google_sheets/scripts/sheets-to-jsonl.py \
  --api-key YOUR_KEY --spreadsheet-id SHEET_ID --sheet "App_Master"

# Custom output directory
python3 sources/community/google_sheets/scripts/sheets-to-jsonl.py \
  --api-key YOUR_KEY --spreadsheet-id SHEET_ID --output /path/to/output
```

Default output directory: `~/.coral/google_sheets/`

**Note:** The `--output` option writes to a custom path, but the manifest reads from `~/.coral/google_sheets/`. Update the manifest `source.location` if using a custom path.

## Tables

### `rows`

Data rows from Google Sheets with column headers as keys in a JSON `data` column. Each row includes spreadsheet ID, sheet name, and row number for multi-sheet queries.

**Columns**

| Column | Type | Description |
|--------|------|-------------|
| `_spreadsheet_id` | Utf8 | Google Spreadsheet ID |
| `_sheet_name` | Utf8 | Sheet tab name within the spreadsheet |
| `_row_number` | Int64 | Row number within the sheet (1-indexed, excluding header) |
| `data` | Json | Row data as a JSON object with column headers as keys |

Use Coral's JSON functions to extract specific fields:
```sql
SELECT json_as_text(data, 'column_name') FROM google_sheets.rows
```

---

### `sheets`

Metadata for each sheet tab in the spreadsheet.

**Columns**

| Column | Type | Description |
|--------|------|-------------|
| `spreadsheet_id` | Utf8 | Google Spreadsheet ID |
| `spreadsheet_title` | Utf8 | Title of the spreadsheet |
| `sheet_name` | Utf8 | Name of the sheet tab |
| `sheet_id` | Int64 | Numeric ID of the sheet tab |
| `sheet_type` | Utf8 | Sheet type (GRID, OBJECT, etc.) |
| `row_count` | Int64 | Number of rows in the sheet |
| `column_count` | Int64 | Number of columns in the sheet |

## Source scope

- File-backed source reading from `~/.coral/google_sheets/rows.jsonl` and `~/.coral/google_sheets/sheets.jsonl`.
- No API key stored in Coral — the converter script uses the key at run time only.
- The converter uses Python stdlib only (`urllib`). No external dependencies.
- Data is static — re-run the converter script to refresh.
- The first row of each sheet is used as column headers for the `data` JSON object.
- Empty cells are represented as `null` in the JSON.
- 2 declared test queries (`rows` + `sheets`) require no filters.

## Limitations

- The spreadsheet must be publicly shared ("Anyone with the link" > Viewer). Private sheets require a service account, which is not supported in this version.
- Spreadsheet columns are stored inside a `data` JSON column — use `json_as_text(data, 'column_name')` to extract specific fields.
- The converter fetches all rows from the API in a single request. Very large sheets (100K+ rows) may be slow or hit API limits.
- Only GRID-type sheets are fetched. Charts, embedded objects, and other sheet types are skipped.
- Formulas are evaluated — the converter receives computed values, not formula text.
- The Google Sheets API has a quota of 60 read requests per minute per project.

## Provider docs

- Google Sheets API: https://developers.google.com/sheets/api/reference/rest
- API keys: https://console.cloud.google.com/apis/credentials
- Enable Sheets API: https://console.cloud.google.com/apis/library/sheets.googleapis.com

## Live validation output

Validated by fetching a public Google Sheet with the converter script.

```bash
$ python3 sources/community/google_sheets/scripts/sheets-to-jsonl.py \
    --api-key YOUR_KEY --spreadsheet-id SHEET_ID --sheet "App_Master"
  Fetching metadata for SHEET_ID...
  Spreadsheet: price (2 sheets)
  → App_Master

  ✓ 565 rows → ~/.coral/google_sheets/rows.jsonl
  ✓ 1 sheets → ~/.coral/google_sheets/sheets.jsonl
```

```bash
$ coral source lint sources/community/google_sheets/manifest.yaml
Manifest is valid
```

```bash
$ coral source add --file sources/community/google_sheets/manifest.yaml
Added source google_sheets

  ✓ google_sheets connected successfully

    google_sheets (2 tables)
    ├─ rows
    └─ sheets
    Query tests
    2 declared · 2 passed · 0 failed

    ✓ SELECT _spreadsheet_id, _sheet_name, _row_number, data FROM google_sheets.rows LIMIT 3
      3 rows

    ✓ SELECT spreadsheet_title, sheet_name, row_count FROM google_sheets.sheets LIMIT 3
      1 row
```

**Live rows proof:**

```sql
SELECT _sheet_name, _row_number, data
FROM google_sheets.rows LIMIT 3;
```

```text
+-------------+-------------+---------------------------------------------------+
| _sheet_name | _row_number | data                                              |
+-------------+-------------+---------------------------------------------------+
| App_Master  | 1           | {"subcategory_id":"appointment_scheduling",...}    |
| App_Master  | 2           | {"subcategory_id":"appointment_scheduling",...}    |
| App_Master  | 3           | {"subcategory_id":"appointment_scheduling",...}    |
+-------------+-------------+---------------------------------------------------+
```

**Live sheets proof:**

```sql
SELECT spreadsheet_title, sheet_name, row_count, column_count
FROM google_sheets.sheets;
```

```text
+-------------------+------------+-----------+--------------+
| spreadsheet_title | sheet_name | row_count | column_count |
+-------------------+------------+-----------+--------------+
| price             | App_Master | 1000      | 21           |
+-------------------+------------+-----------+--------------+
```
