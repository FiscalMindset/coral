# Tavily

**Version:** 0.1.0
**Backend:** HTTP
**Functions:** 1

Query web search results from Tavily. The source provides a provider-native search function that returns ranked results with titles, URLs, content snippets, and relevance scores optimized for LLM consumption.

## Installation

Install the source via the CLI:

```bash
coral source add --file sources/community/tavily/manifest.yaml
```

## Credentials

To use this source, you will need a Tavily API key.

1. Register at [app.tavily.com](https://app.tavily.com).
2. Copy your API key (starts with `tvly-`).
3. Provide it when prompted by `coral source add` or set it as an environment variable:

```bash
export TAVILY_API_KEY="tvly-your-api-key"
```

## Quick Start

```sql
-- Basic web search with provider-native ranking
SELECT url, title, score
FROM tavily.search(q => 'Coral SQL')
LIMIT 5;

-- Search with advanced depth for more comprehensive results
SELECT url, title, content, score
FROM tavily.search(q => 'Coral SQL', search_depth => 'advanced')
LIMIT 3;

-- Filter by news topic within a specific time range
SELECT url, title, published_date, score
FROM tavily.search(q => 'Coral SQL', topic => 'news', time_range => 'week')
LIMIT 5;

-- Include an AI-generated answer from Tavily
SELECT url, title, score
FROM tavily.search(q => 'What is Coral SQL?', include_answer => true)
LIMIT 3;
```

## Functions

### `tavily.search`
Provider-native search for the web. Pass the query as a named argument with `q => '<query>'`.

| Argument / Column | Type | Description |
|--------|------|-------------|
| `q` | Utf8 | (Required) Search query |
| `url` | Utf8 | URL of the search result |
| `title` | Utf8 | Title of the search result |
| `content` | Utf8 | Most query-related content extracted from the source |
| `score` | Float64 | Relevance score of the search result (0 to 1) |
| `raw_content` | Utf8 | Parsed and cleaned HTML content (requires `include_raw_content => true`) |
| `published_date` | Utf8 | Publication date (only for news topic searches) |
| `images` | Json | Images extracted from the result (requires `include_images => true`) |
| `favicon` | Utf8 | Favicon URL for the search result |
| `max_results` | Utf8 | Maximum number of results (default 5, max 20) |
| `search_depth` | Utf8 | Search depth: `basic`, `advanced`, `fast`, or `ultra-fast` |
| `topic` | Utf8 | Topic: `general`, `news`, or `finance` |
| `time_range` | Utf8 | Time range: `day`, `week`, `month`, `year` |
| `include_answer` | Utf8 | Set to `true` to include AI-generated answer |
| `include_images` | Utf8 | Set to `true` to include images |
| `include_raw_content` | Utf8 | Set to `true` to include raw HTML content |

## Live request costs

Calling `tavily.search` performs one live `POST /search` call per SQL query. Tavily charges per search credit; refer to <https://docs.tavily.com/docs/features/pricing> for current rates. Add `LIMIT` to control the number of results returned (max 20).

## Source scope

- Targets Tavily's hosted API at `https://api.tavily.com`.
- Requires `TAVILY_API_KEY` authentication as a Bearer token.
- The `q` argument is required.
- `fetch_limit_default: 5` matches the Tavily API's default `max_results` of 5.
- `include_answer`, `include_images`, and `include_raw_content` are boolean arguments. Pass `true` or `false` (e.g. `include_answer => true`). `include_answer` also accepts `'basic'` or `'advanced'` for a short or detailed answer. `include_raw_content` also accepts `'markdown'` or `'text'` for format control.
- The `score` column is a relevance score between 0 and 1.
- `search_depth` supports `basic`, `advanced`, `fast`, and `ultra-fast`.

## Limitations

- The source models the `POST /search` endpoint only. Other Tavily endpoints are intentionally out of scope.
- `raw_content` is only available when `include_raw_content => true` is passed.
- `published_date` is only populated for news topic searches.
- `favicon` is only available when the search result includes a favicon URL.
- Tavily's top-level `answer` field (when `include_answer` is enabled) is not exposed as a column since it is per-query, not per-result.
- Pagination is not supported; Tavily returns a single page of results per call (max 20).

## Notes

- **Rate Limits:** Rate limits apply based on your Tavily plan. Refer to Tavily's pricing page for details.
- **Nullable Fields:** `raw_content`, `published_date`, `images`, and `favicon` may be `NULL` depending on the arguments passed and the search results returned.

## Provider docs

- Search API reference: https://docs.tavily.com/documentation/api-reference/endpoint/search
- API keys: https://app.tavily.com

## Live validation output

Validated against a live Tavily account with a valid `TAVILY_API_KEY`.

```bash
$ coral source lint sources/community/tavily/manifest.yaml
Manifest is valid
```

```bash
$ coral source add --file sources/community/tavily/manifest.yaml
Added source tavily (secrets: file (plaintext))

  ✓ tavily connected successfully
  Secrets: file (plaintext)
    Query tests
    1 declared · 1 passed · 0 failed

    ✓ SELECT url, title, score FROM tavily.search(q => 'Coral SQL') LIMIT 2
      2 rows
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
  Secrets: file (plaintext)
    Query tests
    1 declared · 1 passed · 0 failed

    ✓ SELECT url, title, score FROM tavily.search(q => 'Coral SQL') LIMIT 2
      2 rows
```

**Live bounded search proof:**

```sql
SELECT url, title, score
FROM tavily.search(q => 'Coral SQL')
LIMIT 3;
```

```text
+---------------------------------------------------------------------------------------------------------------------------------------+-------------------------------------------------------------------------+-----------+
| url                                                                                                                                   | title                                                                   | score     |
+---------------------------------------------------------------------------------------------------------------------------------------+-------------------------------------------------------------------------+-----------+
| https://cdmsworkshop.github.io/2022/Proceedings/InvitedTalks/Abstract_WalaaEldinMoustafa.pdf                                          | [PDF] Coral: A SQL translation and rewrite engine for modern data lakes | 0.8245895 |
| https://www.threads.com/@githubprojects/post/DYtu-WtlAFY/coral-gives-agents-a-local-first-sql-runtime-over-ap-is-files-and-other-data | Coral gives agents a local-first SQL runtime over APIs, files, and ...  | 0.7703443 |
| https://indico.cern.ch/event/408139/contributions/979851/attachments/815802/1117844/coral_CHEP06_paper.pdf                            | [PDF] CORAL, A SOFTWARE SYSTEM FOR VENDOR-NEUTRAL ... - Indico          | 0.7520312 |
+---------------------------------------------------------------------------------------------------------------------------------------+-------------------------------------------------------------------------+-----------+
```
