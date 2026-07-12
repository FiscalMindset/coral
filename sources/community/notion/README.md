# Notion

**Version:** 0.1.0
**Backend:** HTTP
**Functions:** 1

Query pages, databases, and workspace content from Notion. Search across your workspace and retrieve page metadata, database schemas, and content structure through SQL.

## Installation

Install the source via the CLI:

```bash
coral source add --file sources/community/notion/manifest.yaml
```

## Credentials

To use this source, you will need a Notion integration token.

1. Go to [Notion Integrations](https://www.notion.so/profile/integrations).
2. Create a new **internal integration** for your workspace.
3. Copy the integration token (starts with `ntn_`).
4. **Connect the integration** to the pages/databases you want to query (open the page in Notion, click `...` > `Connections` > add your integration).
5. Provide the token when prompted by `coral source add` or set it as an environment variable:

```bash
export NOTION_API_KEY="ntn_your-integration-token"
```

**Note:** The integration can only access pages and databases it has been explicitly connected to. Pages not connected to the integration will not appear in search results.

## Quick Start

```sql
-- List all accessible pages and databases
SELECT id, object, url, created_time
FROM notion.search(q => '')
LIMIT 10;

-- Search for specific content
SELECT id, object, url
FROM notion.search(q => 'Meeting Notes')
LIMIT 5;

-- List only databases
SELECT id, url, title
FROM notion.search(q => '')
WHERE object = 'database';

-- List only pages
SELECT id, url, created_time, last_edited_time
FROM notion.search(q => '')
WHERE object = 'page'
LIMIT 10;

-- Find recently edited content
SELECT id, object, url, last_edited_time
FROM notion.search(q => '')
ORDER BY last_edited_time DESC
LIMIT 5;
```

## Functions

### `notion.search`

Search pages and databases in your Notion workspace. Pass the query as `q => '<query>'`. Use `q => ''` to list all accessible content.

**Arguments**

| Argument | Type | Description |
|----------|------|-------------|
| `q` | Utf8 | (Required) Search query. Use `''` to list all accessible content. |

**Result columns**

| Column | Type | Description |
|--------|------|-------------|
| `id` | Utf8 | Unique identifier for the page or database |
| `object` | Utf8 | Object type (`page` or `database`) |
| `url` | Utf8 | Notion URL for the page or database |
| `created_time` | Timestamp | When the object was created (ISO 8601) |
| `last_edited_time` | Timestamp | When the object was last edited (ISO 8601) |
| `parent` | Json | Parent object (workspace, page_id, or database_id) |
| `in_trash` | Boolean | Whether the object is in the trash |
| `is_archived` | Boolean | Whether the object is archived |
| `properties` | Json | Page properties or database schema (JSON object) |
| `title` | Json | Database title rich text array. Null for pages. |

## Source scope

- Targets the Notion API at `https://api.notion.com/v1` with `Notion-Version: 2022-06-28`.
- Requires `NOTION_API_KEY` authentication as a Bearer token.
- The integration must be connected to specific pages/databases to access them.
- Cursor-based pagination (`start_cursor` / `next_cursor`) with page_size default 10, max 100.
- Search returns both pages and databases — filter with `WHERE object = 'page'` or `WHERE object = 'database'` in SQL.
- 1 declared test query is source-independent.
- Provides read-only access. Creating, updating, or deleting pages, databases, and blocks is out of scope.

## Limitations

- The source models `POST /v1/search` only. Individual page retrieval (`GET /v1/pages/{id}`), block content (`GET /v1/blocks/{id}/children`), and database queries (`POST /v1/databases/{id}/query`) are not exposed in this version.
- Page content (blocks/text) is not returned — only page metadata and properties. Use the Notion API directly for full page content.
- The `title` column contains rich text for databases only. For pages, the title is inside the `properties` JSON under the `title` type property.
- The `properties` column contains the full properties object which varies by page/database schema.
- Personal access tokens cannot list workspace users (`GET /v1/users`). The `users` endpoint is not modeled.
- Only pages/databases connected to the integration are searchable. See the Credentials section for setup.
- Rate limits apply: Notion allows 3 requests per second per integration.

## Provider docs

- Notion API introduction: https://developers.notion.com/docs/getting-started
- Search API: https://developers.notion.com/reference/post-search
- Authentication: https://developers.notion.com/docs/authorization
- Integrations: https://www.notion.so/profile/integrations

## Live validation output

Validated against a live Notion workspace with a valid `NOTION_API_KEY`.

```bash
$ coral source lint sources/community/notion/manifest.yaml
Manifest is valid
```

```bash
$ coral source add --file sources/community/notion/manifest.yaml
Added source notion

  ✓ notion connected successfully

    Query tests
    1 declared · 1 passed · 0 failed

    ✓ SELECT id, object, url FROM notion.search(q => '') LIMIT 3
      3 rows
```

**Function introspection:**

```sql
SELECT function_name, kind, arguments_json
FROM coral.table_functions
WHERE schema_name = 'notion';
```

```text
+---------------+--------+--------------------------------------------+
| function_name | kind   | arguments_json                             |
+---------------+--------+--------------------------------------------+
| search        | search | [{"name":"q","required":true,"values":[]}] |
+---------------+--------+--------------------------------------------+
```

**Inputs introspection:**

```sql
SELECT key, kind, required, is_set
FROM coral.inputs
WHERE schema_name = 'notion';
```

```text
+----------------+--------+----------+--------+
| key            | kind   | required | is_set |
+----------------+--------+----------+--------+
| NOTION_API_KEY | secret | true     | true   |
+----------------+--------+----------+--------+
```

**Live search proof:**

```sql
SELECT id, object, url, created_time, in_trash
FROM notion.search(q => '') LIMIT 5;
```

```text
+--------------------------------------+----------+----------------------------------------------------------+----------------------+----------+
| id                                   | object   | url                                                      | created_time         | in_trash |
+--------------------------------------+----------+----------------------------------------------------------+----------------------+----------+
| d3d04300-0000-0000-0000-014512d331ec | database | https://app.notion.com/p/d3d043...                       | 2026-07-12T05:07:00Z | false    |
| 24f04300-0000-0000-0000-ea18d66063d3 | page     | https://app.notion.com/p/24f043...                       | 2025-08-14T10:43:00Z | false    |
| 8c804300-0000-0000-0000-015a034d6dd0 | page     | https://app.notion.com/p/Vicky-Kumar-8c8043...           | 2025-12-06T17:44:00Z | false    |
| 23704300-0000-0000-0000-ce5849ef2175 | page     | https://app.notion.com/p/Try-AI-Meeting-Notes-237043...  | 2025-07-21T17:22:00Z | false    |
| 19704300-0000-0000-0000-c770be0a569a | page     | https://app.notion.com/p/Student-Job-Tracker-197043...   | 2025-02-11T16:59:00Z | false    |
+--------------------------------------+----------+----------------------------------------------------------+----------------------+----------+
```

**Live search with query proof:**

```sql
SELECT id, object, url
FROM notion.search(q => 'People') LIMIT 3;
```

```text
+--------------------------------------+----------+-----------------------------------------------------------+
| id                                   | object   | url                                                       |
+--------------------------------------+----------+-----------------------------------------------------------+
| d3d04300-0000-0000-0000-014512d331ec | database | https://app.notion.com/p/d3d043...                        |
+--------------------------------------+----------+-----------------------------------------------------------+
```
