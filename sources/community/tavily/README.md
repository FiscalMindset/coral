# Tavily Source

Query web search results from Tavily through SQL. The source provides a search table that returns ranked results with titles, URLs, content snippets, and relevance scores, optimized for LLM consumption.

## Summary

This source lets Coral call Tavily's search API endpoint and expose the ranked search results through SQL. The single live table `tavily.search_results` sends one Tavily search request per SQL query and returns the top results with relevance scores. Supports configurable search depth, topic filtering (general/news), time range, and optional answer and image inclusion.

## Provider docs

- Search API reference:
  https://docs.tavily.com/documentation/api-reference/endpoint/search
- API keys:
  https://app.tavily.com

## Authentication

Create or copy a Tavily API key from the Tavily dashboard, then add the community source:

```bash
coral source add --interactive --file sources/community/tavily/manifest.yaml
```

For scripted setup, provide the key as an environment variable:

```bash
TAVILY_API_KEY=tvly-... coral source add --file sources/community/tavily/manifest.yaml
```

The key is stored locally by Coral and sent in the `Authorization: Bearer <key>` header. Tavily keys start with `tvly-`.

## Live request costs

Selecting the `tavily.search_results` table performs one live `POST /search` call per SQL query. Tavily charges per search credit; refer to <https://docs.tavily.com/docs/features/pricing> for current rates. Add `LIMIT` to control the number of results returned (max 20).

## Source shape

- `tavily.search_results` searches the web through `POST /search` with a required `q` filter and optional `max_results`, `search_depth`, `topic`, `time_range`, `include_answer`, and `include_images` filters.

## Source scope

- Targets Tavily's hosted API at `https://api.tavily.com`.
- Requires `TAVILY_API_KEY` authentication as a Bearer token.
- The search_results table requires the `q` filter (the search query).
- `max_results` is an integer filter that controls how many results to return (default 5, max 20). Pass an integer literal in the `WHERE` clause (e.g. `WHERE max_results = 10`).
- `include_answer` and `include_images` are boolean filters. Pass `true` or `false` (e.g. `WHERE include_answer = true`).
- The `score` column is a relevance score between 0 and 1.

## Limitations

- The source models the `POST /search` endpoint only. Other Tavily endpoints are intentionally out of scope.
- `raw_content` is only available when `include_raw_content` is enabled (not currently modeled as a filter).
- `published_date` is only populated for news topic searches.
- Pagination is not supported; Tavily returns a single page of results per call (max 20).

## Tables

### `tavily.search_results`

Searches the web and returns ranked results.

```sql
SELECT url, title, score
FROM tavily.search_results
WHERE q = 'Coral SQL'
LIMIT 5;
```

Search with advanced depth for more comprehensive results:

```sql
SELECT url, title, content, score
FROM tavily.search_results
WHERE q = 'Coral SQL'
  AND search_depth = 'advanced'
LIMIT 3;
```

Filter by news topic within a specific time range:

```sql
SELECT url, title, published_date, score
FROM tavily.search_results
WHERE q = 'Coral SQL'
  AND topic = 'news'
  AND time_range = 'week'
LIMIT 5;
```

Include an AI-generated answer from Tavily:

```sql
SELECT url, title, score
FROM tavily.search_results
WHERE q = 'What is Coral SQL?'
  AND include_answer = true
LIMIT 3;
```

Useful columns:

| Column | Notes |
|---|---|
| `q` | Search query supplied in the SQL filter (virtual column). |
| `url` | URL of the search result. |
| `title` | Title of the search result. |
| `content` | Most query-related content extracted from the source. |
| `score` | Relevance score of the search result (0 to 1). |
| `raw_content` | Parsed and cleaned HTML content (requires `include_raw_content`). |
| `published_date` | Publication date (only for news topic searches). |
| `images` | Images extracted from the result (requires `include_images`). |

## Live validation output

Validated against a live Tavily account with a valid `TAVILY_API_KEY`.

```bash
$ coral source lint sources/community/tavily/manifest.yaml
Manifest is valid
```

```bash
$ coral source add --file sources/community/tavily/manifest.yaml
Added source tavily

  ✓ tavily connected successfully

    tavily (1 table)
    └─ search_results
    Query tests
    1 declared · 1 passed · 0 failed
```

**Tables introspection:**

```sql
SELECT schema_name, table_name, description, required_filters
FROM coral.tables
WHERE schema_name = 'tavily'
ORDER BY table_name;
```

```text
+-------------+----------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------+------------------+
| schema_name | table_name     | description                                                                                                                                                                 | required_filters |
+-------------+----------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------+------------------+
| tavily      | search_results | Web search results from Tavily. Use `q % '<query>'` for provider-ranked search. Returns titles, URLs, content snippets, and relevance scores optimized for LLM consumption. | q                |
+-------------+----------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------+------------------+
```

**Columns introspection:**

```sql
SELECT table_name, column_name, data_type, is_required_filter
FROM coral.columns
WHERE schema_name = 'tavily'
ORDER BY table_name, ordinal_position;
```

```text
+----------------+----------------+-----------+--------------------+
| table_name     | column_name    | data_type | is_required_filter |
+----------------+----------------+-----------+--------------------+
| search_results | q              | Utf8      | true               |
| search_results | url            | Utf8      | false              |
| search_results | title          | Utf8      | false              |
| search_results | content        | Utf8      | false              |
| search_results | score          | Float64   | false              |
| search_results | raw_content    | Utf8      | false              |
| search_results | published_date | Utf8      | false              |
| search_results | images         | Json      | false              |
+----------------+----------------+-----------+--------------------+
```

**Inputs introspection:**

```sql
SELECT key, kind, required, is_set
FROM coral.inputs
WHERE schema_name = 'tavily'
ORDER BY key;
```

```text
+----------------+--------+----------+--------+
| key            | kind   | required | is_set |
+----------------+--------+----------+--------+
| TAVILY_API_KEY | secret | true     | true   |
+----------------+--------+----------+--------+
```

```bash
$ coral source test tavily
  ✓ tavily connected successfully

    tavily (1 table)
    └─ search_results
    Query tests
    1 declared · 1 passed · 0 failed

    ✓ SELECT url, title, score FROM tavily.search_results WHERE q = 'Coral SQL' LIMIT 2
      2 rows
```

**Live bounded search proof:**

```sql
SELECT url, title, score
FROM tavily.search_results
WHERE q = 'Coral SQL'
LIMIT 3;
```

```text
+---------------------------------------------------------------------------------------------------------------------------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+------------+
| url                                                                                                                                   | title                                                                                                                                                                                                                                                                                                                                                                                                                                                             | score      |
+---------------------------------------------------------------------------------------------------------------------------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+------------+
| https://cdmsworkshop.github.io/2022/Proceedings/InvitedTalks/Abstract_WalaaEldinMoustafa.pdf                                          | [PDF] Coral: A SQL translation and rewrite engine for modern data lakes                                                                                                                                                                                                                                                                                                                                                                                           | 0.7931224  |
| https://www.threads.com/@githubprojects/post/DYtu-WtlAFY/coral-gives-agents-a-local-first-sql-runtime-over-ap-is-files-and-other-data | Coral gives agents a local-first SQL runtime over APIs, files, and other data sources, replacing bespoke tool glue with one query interface. - Query multiple live sources through SQL from the CLI or over MCP - Join across sources like GitHub, Linear, and local files in a single statement - 20% more accurate and 2x more cost efficient than direct provider MCPs in benchmarks - Write custom source specs as YAML files to expose any API as SQL tables | 0.77405477 |
| https://indico.cern.ch/event/408139/contributions/979851/attachments/815802/1117844/coral_CHEP06_paper.pdf                            | [PDF] CORAL, A SOFTWARE SYSTEM FOR VENDOR-NEUTRAL ... - Indico                                                                                                                                                                                                                                                                                                                                                                                                    | 0.7520312  |
+---------------------------------------------------------------------------------------------------------------------------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+------------+
```
