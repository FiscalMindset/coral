# Cloudinary

**Version:** 0.1.0
**Backend:** HTTP
**Tables:** 5
**Base URL:** `https://api.cloudinary.com/v1_1/<cloud_name>`

Query assets, folders, upload presets, usage details, and metadata fields from Cloudinary via the Cloudinary Admin API. Provides read-only access to media asset inventory and account configuration using API Key and API Secret authentication.

## Installation

Install the source via the CLI:

```bash
coral source add --file sources/community/cloudinary/manifest.yaml
```

## Credentials

To use this source, you need your Cloudinary cloud name and API credentials.

1. Log in to the [Cloudinary Console](https://console.cloudinary.com).
2. Copy your **cloud name** from the Account Details section at the top of the dashboard.
3. Navigate to **Settings → Access Keys**.
4. Copy the **API Key** and **API Secret** (or generate a new key pair if none exists).
5. Base64-encode `api_key:api_secret` to create the Basic auth token:

```bash
printf '%s:%s' YOUR_API_KEY YOUR_API_SECRET | base64
```

6. Provide all values as environment variables or when prompted by `coral source add`:

```bash
export CLOUDINARY_CLOUD_NAME="your-cloud-name"
export CLOUDINARY_BASIC_AUTH="base64-encoded-api-key:api-secret"
```

## Quick Start

```sql
-- Verify connectivity and get usage details
SELECT plan, credits_usage, credits_limit, storage_bytes, bandwidth_bytes
FROM cloudinary.usage;

-- List recent assets
SELECT public_id, resource_type, format, bytes, width, height, created_at
FROM cloudinary.resources
LIMIT 10;

-- List all top-level folders
SELECT name, path
FROM cloudinary.folders;

-- List all upload presets
SELECT name, unsigned, settings
FROM cloudinary.upload_presets;

-- List all metadata field definitions
SELECT external_id, label, type, mandatory
FROM cloudinary.metadata_fields;
```

## Tables

### `resources`

Assets (images, videos, raw files, etc.) stored in your Cloudinary product environment. Returns metadata such as public ID, format, dimensions, file size, tags, and context.

**Filters**

| Filter | Type | Required | Description |
|--------|------|----------|-------------|
| `resource_type` | Utf8 | | Filter by type (image, video, raw, auto) |
| `type` | Utf8 | | Filter by delivery type (upload, private, authenticated) |
| `prefix` | Utf8 | | Filter by folder prefix (e.g. myfolder/subfolder) |
| `start_at` | Utf8 | | Filter by minimum created_at date (ISO 8601) |
| `direction` | Utf8 | | Sort direction (asc or desc, default: desc by date) |
| `tags` | Boolean | | Set to true to include tags JSON column |
| `context` | Boolean | | Set to true to include context JSON column |
| `metadata` | Boolean | | Set to true to include metadata_fields JSON column |

**Columns**

| Column | Type | Description |
|--------|------|-------------|
| `public_id` | Utf8 | Unique identifier for the asset |
| `asset_id` | Utf8 | Immutable asset identifier |
| `format` | Utf8 | File format extension (e.g. jpg, png, mp4) |
| `version` | Int64 | Version number of the asset |
| `resource_type` | Utf8 | Type of resource (image, video, raw, auto) |
| `type` | Utf8 | Delivery type (upload, private, authenticated, etc.) |
| `created_at` | Timestamp | When the asset was created (ISO 8601) |
| `bytes` | Int64 | File size in bytes |
| `width` | Int64 | Width of the asset in pixels |
| `height` | Int64 | Height of the asset in pixels |
| `url` | Utf8 | HTTP URL of the asset |
| `secure_url` | Utf8 | HTTPS URL of the asset |
| `tags` | Json | JSON array of tag strings. Populated when tags=true filter is set |
| `context` | Json | JSON object of custom context metadata. Populated when context=true filter is set |
| `metadata_fields` | Json | JSON object of structured metadata field values. Populated when metadata=true filter is set |
| `etag` | Utf8 | ETag of the uploaded file |
| `placeholder` | Boolean | Whether the asset is a placeholder |

---

### `folders`

Top-level asset folders in your Cloudinary product environment. Only returns folders, not subfolders (use the `prefix` filter on the `resources` table to browse subfolder contents).

**Columns**

| Column | Type | Description |
|--------|------|-------------|
| `name` | Utf8 | Display name of the folder |
| `path` | Utf8 | Full path of the folder |

---

### `upload_presets`

Upload presets configured in your Cloudinary product environment. Each preset defines default settings for uploaded assets such as transformation, folder, tags, and access control.

**Columns**

| Column | Type | Description |
|--------|------|-------------|
| `name` | Utf8 | Name of the upload preset |
| `unsigned` | Boolean | Whether the preset allows unsigned uploads |
| `settings` | Json | JSON object of preset settings (folder, tags, transformations, etc.) |

---

### `usage`

Current usage details for the Cloudinary product environment, including plan type, credits consumption, storage usage, bandwidth, and transformations performed. Returns exactly one row.

**Columns**

| Column | Type | Description |
|--------|------|-------------|
| `plan` | Utf8 | Cloudinary plan name (e.g. Free, Advanced, Enterprise) |
| `credits_usage` | Int64 | Credits consumed in the current billing period |
| `credits_limit` | Int64 | Total credits available in the current billing period |
| `credits_used_percentage` | Float64 | Percentage of credits used |
| `storage_bytes` | Int64 | Total storage used in bytes |
| `storage_limit_bytes` | Int64 | Storage limit in bytes |
| `bandwidth_bytes` | Int64 | Bandwidth used in bytes |
| `bandwidth_limit_bytes` | Int64 | Bandwidth limit in bytes |
| `transformations_used` | Int64 | Number of transformations performed |
| `transformations_limit` | Int64 | Transformation limit |
| `objects_count` | Int64 | Total number of assets stored |
| `objects_limit` | Int64 | Asset count limit |

---

### `metadata_fields`

Structured metadata field definitions configured in the Cloudinary product environment. Includes field type, label, default value, validation rules, and mandatory status.

**Columns**

| Column | Type | Description |
|--------|------|-------------|
| `external_id` | Utf8 | Unique identifier for the metadata field |
| `label` | Utf8 | Display label for the metadata field |
| `type` | Utf8 | Data type of the metadata field (integer, string, date, etc.) |
| `mandatory` | Boolean | Whether the field is required when uploading assets |
| `default_value` | Utf8 | Default value assigned when no value is provided |
| `validation` | Json | JSON object defining validation rules for the field |

## Live request costs

Each table query performs at least one live API call to `https://api.cloudinary.com/v1_1/<cloud_name>`. Cursor-based pagination on `resources`, `folders`, and `upload_presets` may trigger additional calls when `LIMIT` exceeds a single page's results. See the [Cloudinary Admin API reference](https://cloudinary.com/documentation/admin_api) for rate limit details.

## Source scope

- Targets the Cloudinary Admin API at `https://api.cloudinary.com/v1_1/<cloud_name>`.
- Requires `CLOUDINARY_CLOUD_NAME` (base URL variable) and `CLOUDINARY_BASIC_AUTH` (HTTP Basic Auth header).
- Covers read-only access: asset listing with filters, folder listing, upload preset listing, usage details, and metadata field definitions.
- Cursor-based pagination (`next_cursor` query param) on `resources`, `folders`, and `upload_presets` — uses `response_cursor_path` for response cursor extraction.
- The `usage` table exposes nested child objects (credits, storage, bandwidth, transformations, objects) as flat columns with nullable types — the API may omit deeply nested fields depending on plan.
- 8 optional filters on `resources` for filtering by resource type, delivery type, folder prefix, date range, sort direction, and inclusion of tags/context/metadata.
- 2 declared test queries (resources + folders LIMIT 5) are source-independent and work on any account regardless of data.
- Column definitions are validated against the [Cloudinary Admin API reference](https://cloudinary.com/documentation/admin_api).

## Limitations

- The source provides read-only access. Asset upload, deletion, transformation, and other mutating operations are intentionally out of scope.
- The `tags` endpoint (`GET /tags`) is excluded — it returns `404 Not Found` on Free plan accounts. Tag data is still accessible via the `tags` boolean filter on the `resources` table.
- The `folders` table returns only top-level folders. Subfolder navigation requires the `prefix` filter on `resources`.
- `metadata_fields` has no pagination — the API returns all metadata fields in a single response (typically a small set).
- The `usage` table has no pagination — it is a single-object response.
- Cloudinary enforces plan-based rate limits. Free plan accounts have a limit of 500 credits per hour for Admin API calls.

## Provider docs

- Cloudinary Admin API reference: https://cloudinary.com/documentation/admin_api
- Cloudinary Console (credentials): https://console.cloudinary.com
- Authentication: https://cloudinary.com/documentation/admin_api#authentication

## Live validation output

Validated against a live Cloudinary Free plan account with a valid `CLOUDINARY_CLOUD_NAME` and `CLOUDINARY_BASIC_AUTH`.

```bash
$ coral source lint sources/community/cloudinary/manifest.yaml
Manifest is valid
```

```bash
$ coral source add --file sources/community/cloudinary/manifest.yaml
Added source cloudinary

  ✓ cloudinary connected successfully

    cloudinary (5 tables)
    ├─ folders
    ├─ metadata_fields
    ├─ resources
    ├─ upload_presets
    └─ usage
    Query tests
    2 declared · 2 passed · 0 failed

    ✓ SELECT public_id, resource_type, format, bytes, created_at FROM cloudinary.resources LIMIT 5
      0 rows

    ✓ SELECT name FROM cloudinary.folders LIMIT 5
      1 row
```

**Table introspection:**

```sql
SELECT table_name, description, required_filters
FROM coral.tables
WHERE schema_name = 'cloudinary'
ORDER BY table_name;
```

```text
+-----------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+------------------+
| table_name      | description                                                                                                                                                                             | required_filters |
+-----------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+------------------+
| folders         | Top-level asset folders in your Cloudinary product environment. Only returns folders, not subfolders (use the prefix filter on the resources table to browse subfolder contents). |                  |
| metadata_fields | Structured metadata field definitions configured in the Cloudinary product environment. Includes field type, label, default value, validation rules, and mandatory status.              |                  |
| resources       | Assets (images, videos, raw files, etc.) stored in your Cloudinary product environment. Returns metadata such as public ID, format, dimensions, file size, tags, and context.           |                  |
| upload_presets  | Upload presets configured in your Cloudinary product environment. Each preset defines default settings for uploaded assets such as transformation, folder, tags, and access control.    |                  |
| usage           | Current usage details for the Cloudinary product environment, including plan type, credits consumption, storage usage, bandwidth, and transformations performed.                        |                  |
+-----------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+------------------+
```

**Inputs introspection:**

```sql
SELECT key, kind, required, is_set
FROM coral.inputs
WHERE schema_name = 'cloudinary'
ORDER BY key;
```

```text
+-----------------------+----------+----------+--------+
| key                   | kind     | required | is_set |
+-----------------------+----------+----------+--------+
| CLOUDINARY_BASIC_AUTH | secret   | true     | true   |
| CLOUDINARY_CLOUD_NAME | variable | true     | true   |
+-----------------------+----------+----------+--------+
```

**Live usage proof:**

```sql
SELECT plan, credits_usage, credits_limit, credits_used_percentage,
       storage_bytes, storage_limit_bytes, bandwidth_bytes,
       bandwidth_limit_bytes
FROM cloudinary.usage;
```

```text
+------+---------------+---------------+-------------------------+---------------+---------------------+-----------------+-----------------------+
| plan | credits_usage | credits_limit | credits_used_percentage | storage_bytes | storage_limit_bytes | bandwidth_bytes | bandwidth_limit_bytes |
+------+---------------+---------------+-------------------------+---------------+---------------------+-----------------+-----------------------+
| Free | 0             | 25            | 0.0                     | 0             |                     | 0               |                       |
+------+---------------+---------------+-------------------------+---------------+---------------------+-----------------+-----------------------+
```

**Live folders proof:**

```sql
SELECT name, path
FROM cloudinary.folders;
```

```text
+---------+---------+
| name    | path    |
+---------+---------+
| samples | samples |
+---------+---------+
```

**Live resources proof:**

```sql
SELECT public_id, resource_type, format, bytes, width, height, created_at
FROM cloudinary.resources
LIMIT 5;
```

```text
(0 rows — account currently has no uploaded assets)
```
