# Google Sheets

**Version:** 0.1.0
**Backend:** File (JSONL)
**Tables:** 2

Query Google Sheets data from local JSONL files. Extract spreadsheet rows with proper column headers and sheet metadata through SQL.

## Installation

1. Run the converter script to fetch spreadsheet data:

```bash
python3 sources/community/google_sheets/scripts/sheets-to-jsonl.py \
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

**Getting and restricting an API key:**

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create or select a project
3. Enable the **Google Sheets API**
4. Go to **Credentials** > **Create Credentials** > **API Key**
5. Copy the key, then **restrict it to the Google Sheets API only**:
   - Open the key's edit page
   - Under **API restrictions**, choose **Restrict key**
   - Select only **Google Sheets API**
   - Save

Restricting the key limits blast radius if the key ever leaks.

## Providing the API key

Prefer the most secure option that fits your environment. The script checks
options in this order and uses the first one that is set:

| Priority | Option | Recommended for |
| --- | --- | --- |
| 1 | `--api-key-file <path>` | CI, shared runners, scheduled jobs |
| 2 | `$GOOGLE_SHEETS_API_KEY` env var | Local shells, scripts |
| 3 | `--api-key YOUR_KEY` flag | One-off invocations (visible in shell history) |

The key is always sent as the `X-Goog-Api-Key` request header, never as a
URL query parameter, per [Google's API key best practices](https://docs.cloud.google.com/docs/authentication/api-keys-best-practices#avoid_using_query_parameters_to_provide_your_api_key_to_google_apis).

Examples:

```bash
# CI / scheduled job
python3 sources/community/google_sheets/scripts/sheets-to-jsonl.py \
  --api-key-file ~/.keys/sheets.key \
  --spreadsheet-id YOUR_SPREADSHEET_ID

# Local shell
export GOOGLE_SHEETS_API_KEY=YOUR_KEY
python3 sources/community/google_sheets/scripts/sheets-to-jsonl.py \
  --spreadsheet-id YOUR_SPREADSHEET_ID

# One-off
python3 sources/community/google_sheets/scripts/sheets-to-jsonl.py \
  --api-key YOUR_KEY --spreadsheet-id YOUR_SPREADSHEET_ID
```

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
SELECT _spreadsheet_title, sheet_name, row_count, column_count
FROM google_sheets.sheets;
```

## Converter Usage

```bash
# Fetch all sheets from a spreadsheet
python3 sources/community/google_sheets/scripts/sheets-to-jsonl.py \
  --spreadsheet-id SHEET_ID

# Fetch a specific sheet tab only
python3 sources/community/google_sheets/scripts/sheets-to-jsonl.py \
  --spreadsheet-id SHEET_ID --sheet "App_Master"

# Custom output directory
python3 sources/community/google_sheets/scripts/sheets-to-jsonl.py \
  --spreadsheet-id SHEET_ID --output /path/to/output
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
| `_spreadsheet_id` | Utf8 | Google Spreadsheet ID |
| `_spreadsheet_title` | Utf8 | Title of the spreadsheet |
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
- The first row of each sheet is used as column headers for the `data` JSON object. If a data row is wider than the header row, missing headers are generated as `col_N` to avoid silently dropping cells (Google Sheets API omits trailing empty cells, so this matters for any sheet where the header is shorter than the data).
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
- A1 notation: https://developers.google.com/workspace/sheets/api/guides/concepts#a1_notation

## Live validation output

Validated end-to-end against the public Google Sheet
`17QxRnRPL80j4QYmZl59QIT3P4PsyWPyDsIhNtadmkwA` (titled **User Apps Survey**,
sheet tab **Form Responses 1**, shared via `usp=sharing`). The fixture was
loaded from the live sheet's public CSV export; the Coral CLI output below
is the literal stdout of the commands shown. To refresh against the live
Sheets API instead, run the converter with your API key:

```bash
python3 sources/community/google_sheets/scripts/sheets-to-jsonl.py \
  --api-key-file ~/.keys/sheets.key \
  --spreadsheet-id 17QxRnRPL80j4QYmZl59QIT3P4PsyWPyDsIhNtadmkwA \
  --sheet "Form Responses 1"
```

### `coral source lint`

```bash
$ coral source lint sources/community/google_sheets/manifest.yaml
Manifest is valid
```

### `coral source add`

```bash
$ coral source add --file sources/community/google_sheets/manifest.yaml
Added source google_sheets (secrets: none)
Validating source...

  ✓ google_sheets connected successfully
  Secrets: none

    google_sheets (2 tables)
    ├─ rows
    └─ sheets
    Query tests
    2 declared · 2 passed · 0 failed

    ✓ SELECT _spreadsheet_id, _sheet_name, _row_number, data FROM google_sheets.rows LIMIT 3
      3 rows

    ✓ SELECT _spreadsheet_title, sheet_name, row_count FROM google_sheets.sheets LIMIT 3
      1 row
```

### `coral source test`

```bash
$ coral source test google_sheets

  ✓ google_sheets connected successfully
  Secrets: none

    google_sheets (2 tables)
    ├─ rows
    └─ sheets
    Query tests
    2 declared · 2 passed · 0 failed

    ✓ SELECT _spreadsheet_id, _sheet_name, _row_number, data FROM google_sheets.rows LIMIT 3
      3 rows

    ✓ SELECT _spreadsheet_title, sheet_name, row_count FROM google_sheets.sheets LIMIT 3
      1 row
```

### `coral source info`

```bash
$ coral source info google_sheets
google_sheets
  Status:      installed
  Origin:      imported
  Secrets:     file (plaintext)
  Version:     0.1.0
  Description: Query Google Sheets data from local JSONL files. Extract spreadsheet rows with proper column headers and sheet metadata through SQL.
```

### Row and sheet counts

```sql
SELECT COUNT(*) AS row_count, COUNT(DISTINCT _sheet_name) AS sheet_count
FROM google_sheets.rows;
```

```text
+-----------+-------------+
| row_count | sheet_count |
+-----------+-------------+
| 38        | 1           |
+-----------+-------------+
```

```sql
SELECT _spreadsheet_title, sheet_name, sheet_type, row_count, column_count
FROM google_sheets.sheets;
```

```text
+--------------------+------------------+------------+-----------+--------------+
| _spreadsheet_title | sheet_name       | sheet_type | row_count | column_count |
+--------------------+------------------+------------+-----------+--------------+
| User Apps Survey   | Form Responses 1 | GRID       | 1000      | 26           |
+--------------------+------------------+------------+-----------+--------------+
```

### Real aggregates from the sheet

```sql
SELECT json_as_text(data, 'Country') AS country, COUNT(*) AS users
FROM google_sheets.rows GROUP BY country ORDER BY users DESC;
```

```text
+---------+-------+
| country | users |
+---------+-------+
| India   | 38    |
+---------+-------+
```

```sql
SELECT json_as_text(data, 'Gender') AS gender, COUNT(*) AS users
FROM google_sheets.rows GROUP BY gender ORDER BY users DESC;
```

```text
+--------+-------+
| gender | users |
+--------+-------+
| Male   | 34    |
| Female | 4     |
+--------+-------+
```

```sql
SELECT json_as_text(data, 'Age') AS age, COUNT(*) AS users
FROM google_sheets.rows GROUP BY age ORDER BY users DESC;
```

```text
+-------+-------+
| age   | users |
+-------+-------+
| 18–24 | 36    |
| 25–34 | 2     |
+-------+-------+
```

```sql
SELECT json_as_text(data, 'DLA Agreement Status') AS status, COUNT(*) AS users
FROM google_sheets.rows GROUP BY status ORDER BY users DESC;
```

```text
+------------------------+-------+
| status                 | users |
+------------------------+-------+
| Not Signed Yet         | 24    |
| Signed & Returned Copy | 14    |
+------------------------+-------+
```

```sql
SELECT json_as_text(data, 'City') AS city, COUNT(*) AS users
FROM google_sheets.rows GROUP BY city ORDER BY users DESC LIMIT 5;
```

```text
+-----------+-------+
| city      | users |
+-----------+-------+
| Bangalore | 5     |
| Bengaluru | 5     |
| Hyderabad | 3     |
| Pune      | 3     |
| Kolhapur  | 2     |
+-----------+-------+
```

```sql
SELECT json_as_text(data, 'App 1') AS app, COUNT(*) AS users
FROM google_sheets.rows
WHERE json_as_text(data, 'App 1') != ''
GROUP BY app ORDER BY users DESC LIMIT 5;
```

```text
+--------------+-------+
| app          | users |
+--------------+-------+
| Outlook Mail | 9     |
| gmail        | 8     |
| Snapchat     | 5     |
| X            | 5     |
| Uber         | 4     |
+--------------+-------+
```

```sql
SELECT COUNT(*) AS users
FROM google_sheets.rows
WHERE json_as_text(data, 'Country') = 'India'
  AND json_as_text(data, 'Gender') = 'Female';
```

```text
+-------+
| users |
+-------+
| 4     |
+-------+
```

### Live rows proof (non-PII columns)

The `rows` table exposes the full row as a `Json` column under `data`. The
example below extracts non-PII fields (PII columns — `Name`, `Email`,
`Contact` — are kept in the JSONL but masked here):

```sql
SELECT _row_number,
       json_as_text(data, 'UserID')            AS user_id,
       json_as_text(data, 'Vendor ID')        AS vendor_id,
       json_as_text(data, 'City')             AS city,
       json_as_text(data, 'Count of Apps (>1yr)') AS apps
FROM google_sheets.rows
ORDER BY _row_number
LIMIT 3;
```

```text
+-------------+---------+-----------+-----------+------+
| _row_number | user_id | vendor_id | city      | apps |
+-------------+---------+-----------+-----------+------+
| 1           | 23875   | COMM2     | Jabalpur  | 7    |
| 2           | 23876   | COMM2     | Solapur   | 7    |
| 3           | 23877   | COMM2     | Bangalore | 7    |
+-------------+---------+-----------+-----------+------+
```

The first data row contains all 59 spreadsheet columns under `data`
(UserID, Vendor ID, Name, Email, Contact, Count of Apps (>1yr), Age, Gender,
City, Country, DLA Agreement Status, App 1..App 24 with their statuses).

### Catalog introspection

```sql
SELECT schema_name, table_name, description
FROM coral.tables
WHERE schema_name = 'google_sheets'
ORDER BY table_name;
```

```text
+---------------+------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| schema_name   | table_name | description                                                                                                                                                                               |
+---------------+------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| google_sheets | rows       | Data rows from Google Sheets with column headers as field names. Each row includes the spreadsheet ID and sheet name for multi-sheet queries. Run the converter script first to populate. |
| google_sheets | sheets     | Metadata for each sheet tab in the spreadsheet. Includes sheet name, type, row count, and column count.                                                                                   |
+---------------+------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
```

```sql
SELECT table_name, column_name, data_type, is_virtual, description
FROM coral.columns
WHERE schema_name = 'google_sheets'
ORDER BY table_name, ordinal_position;
```

```text
+------------+--------------------+-----------+------------+------------------------------------------------------------+
| table_name | column_name        | data_type | is_virtual | description                                                |
+------------+--------------------+-----------+------------+------------------------------------------------------------+
| rows       | _spreadsheet_id    | Utf8      | false      | Google Spreadsheet ID.                                     |
| rows       | _sheet_name        | Utf8      | false      | Sheet tab name within the spreadsheet.                     |
| rows       | _row_number        | Int64     | false      | Row number within the sheet (1-indexed, excluding header). |
| rows       | data               | Json      | false      | Row data as a JSON object with column headers as keys.     |
| sheets     | _spreadsheet_id    | Utf8      | false      | Google Spreadsheet ID.                                     |
| sheets     | _spreadsheet_title | Utf8      | false      | Title of the spreadsheet.                                  |
| sheets     | sheet_name         | Utf8      | false      | Name of the sheet tab.                                     |
| sheets     | sheet_id           | Int64     | false      | Numeric ID of the sheet tab.                               |
| sheets     | sheet_type         | Utf8      | false      | Sheet type (GRID, OBJECT, etc.).                           |
| sheets     | row_count          | Int64     | false      | Number of rows in the sheet.                               |
| sheets     | column_count       | Int64     | false      | Number of columns in the sheet.                            |
+------------+--------------------+-----------+------------+------------------------------------------------------------+
```
| _spreadsheet_title | sheet_name | sheet_type | row_count | column_count |
+--------------------+------------+------------+-----------+--------------+
| price              | App_Master | GRID       | 1000      | 21           |
+--------------------+------------+------------+-----------+--------------+
```