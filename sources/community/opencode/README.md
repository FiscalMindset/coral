# OpenCode community source

Query a local OpenCode session store through Coral SQL. The source
exposes session metadata (titles, projects, directories, agents,
models, token and cost totals), the AI providers configured for the
server, and the permission rules the server has saved. Read-only.

**Version:** 0.1.0
**Backend:** HTTP
**Tables:** 3
**Table functions:** 1
**Default base URL:** `http://127.0.0.1:14096`

## Provider docs

- Server CLI: <https://opencode.ai/docs/cli>
- `opencode serve` reference: <https://opencode.ai/docs/server>
- HTTP API surface (served at `<base_url>/doc`): `GET /api/session`,
  `GET /api/session/{id}`, `GET /api/provider`,
  `GET /api/permission/saved`

## Installation

Start the opencode server first, then add the source:

```bash
opencode serve --port 14096 --hostname 127.0.0.1 &
coral source add --file sources/community/opencode/manifest.yaml
```

The source uses `OPENCODE_URL` as a non-secret variable. If unset, it
defaults to the local server on port 14096:

```bash
export OPENCODE_URL="http://127.0.0.1:14096"
coral source add --file sources/community/opencode/manifest.yaml
```

This first version targets a local or self-hosted `opencode serve`
instance that does not require authentication. Servers started with the
`OPENCODE_SERVER_PASSWORD` environment variable require HTTP Basic
auth (username `opencode`) that this source does not yet negotiate;
omit the env var when starting the server for v0.1.0.

## Tables

| Table | Description | Required filters |
| --- | --- | --- |
| `opencode.sessions` | All sessions known to the server from `GET /api/session`. | None |
| `opencode.providers` | AI providers configured for the server from `GET /api/provider`. | None |
| `opencode.saved_permissions` | Saved permission rules from `GET /api/permission/saved`. | None |

### `opencode.sessions`

One row per session. Pages through the opaque `cursor.next` value
returned by `GET /api/session`. Timestamps (`created`, `updated`) are
epoch milliseconds.

```sql
SELECT id, title, agent, model_provider, tokens_input, tokens_output, cost
FROM opencode.sessions
LIMIT 5;
```

### `opencode.providers`

One row per AI provider known to the opencode server. The `request`
field on each provider, which may carry an `apiKey`, is intentionally
not exposed.

```sql
SELECT id, name, api_type, api_url
FROM opencode.providers
WHERE api_url IS NOT NULL
ORDER BY id
LIMIT 10;
```

### `opencode.saved_permissions`

One row per saved permission rule. May be empty when no rules have
been saved for any project.

```sql
SELECT id, project_id, action, resource
FROM opencode.saved_permissions
LIMIT 50;
```

## Table functions

| Function | Description |
| --- | --- |
| `opencode.session(id)` | Single-session detail from `GET /api/session/{id}`. |

### `opencode.session`

Fetch full detail for one session. Returns the same column shape as
the `sessions` table for a single row.

```sql
SELECT id, title, agent, model_provider, cost, created, updated
FROM opencode.session(id => 'ses_...');
```

## Example queries

Find the most expensive sessions this month:

```sql
SELECT id, title, model_provider, cost, tokens_input + tokens_output AS total_tokens
FROM opencode.sessions
ORDER BY cost DESC
LIMIT 5;
```

Count sessions per agent:

```sql
SELECT agent, count(*) AS sessions
FROM opencode.sessions
GROUP BY agent
ORDER BY sessions DESC;
```

List providers that route through an OpenAI-compatible SDK:

```sql
SELECT id, name, api_url
FROM opencode.providers
WHERE api_package = '@ai-sdk/openai-compatible'
ORDER BY id;
```

## Validation

Run these checks with `opencode serve` running:

```bash
coral source lint sources/community/opencode/manifest.yaml
coral source add --file sources/community/opencode/manifest.yaml
coral source test opencode
```

The declared tests do not depend on the server's specific data
contents (they pass even when no sessions or providers are present),
but they still require `opencode serve` to be running:

```sql
SELECT id, title FROM opencode.sessions LIMIT 3;

SELECT id, name FROM opencode.providers LIMIT 5;
```

For live validation proof in a PR, include sanitized output for the
commands above plus at least one `opencode.session(id => '...')`
detail call and one aggregate `opencode.sessions` query.

### Live validation output

The following output was captured against a local `opencode serve`
instance. The test machine had 16 configured providers and hundreds
of historical sessions across multiple working directories.

```text
$ coral source lint sources/community/opencode/manifest.yaml
Manifest is valid
```

```text
$ coral source add --file sources/community/opencode/manifest.yaml
Added source opencode (secrets: none)
Validating source...

  ✓ opencode connected successfully
  Secrets: none

    opencode (3 tables)
    ├─ providers
    ├─ saved_permissions
    └─ sessions

    opencode (1 table function)
    └─ session
    Query tests
    2 declared · 2 passed · 0 failed

    ✓ SELECT id, title FROM opencode.sessions LIMIT 3
      3 rows

    ✓ SELECT id, name FROM opencode.providers LIMIT 5
      5 rows
```

```text
$ coral source test opencode

  ✓ opencode connected successfully
  Secrets: none

    opencode (3 tables)
    ├─ providers
    ├─ saved_permissions
    └─ sessions

    opencode (1 table function)
    └─ session
    Query tests
    2 declared · 2 passed · 0 failed

    ✓ SELECT id, title FROM opencode.sessions LIMIT 3
      3 rows

    ✓ SELECT id, name FROM opencode.providers LIMIT 5
      5 rows
```

**Table introspection:**

```sql
SELECT table_name FROM coral.tables WHERE schema_name = 'opencode' ORDER BY table_name;
```

```text
+-------------------+
| table_name        |
+-------------------+
| providers         |
| saved_permissions |
| sessions          |
+-------------------+
```

**Function introspection:**

```sql
SELECT function_name, kind, arguments_json
FROM coral.table_functions
WHERE schema_name = 'opencode'
ORDER BY function_name;
```

```text
+---------------+-------+---------------------------------------------+
| function_name | kind  | arguments_json                              |
+---------------+-------+---------------------------------------------+
| session       | table | [{"name":"id","required":true,"values":[]}] |
+---------------+-------+---------------------------------------------+
```

**Inputs introspection:**

```sql
SELECT key, kind, required, is_set
FROM coral.inputs
WHERE schema_name = 'opencode'
ORDER BY key;
```

```text
+--------------+----------+----------+--------+
| key          | kind     | required | is_set |
+--------------+----------+----------+--------+
| OPENCODE_URL | variable | false    | true   |
+--------------+----------+----------+--------+
```

**Live sessions proof:**

```sql
SELECT id, title, agent, model_provider, tokens_input, tokens_output, cost
FROM opencode.sessions
LIMIT 5;
```

```text
+--------------------------------+---------------------------------------------------+-------+----------------+--------------+---------------+------+
| id                             | title                                             | agent | model_provider | tokens_input | tokens_output | cost |
+--------------------------------+---------------------------------------------------+-------+----------------+--------------+---------------+------+
| ses_fa97a98bcffeopz53rsAqRyg7H | New session - 2026-08-31T06:32:58.435Z            | build | samagama       | 551325       | 9005          | 0.0  |
| ses_fa989d12effe5jSAyQQzBbTwhh | Blindfold repo score validation                   | build | samagama       | 611345       | 2627          | 0.0  |
| ses_fa9928555ffetthUA0mibXC7PT | Verifying agentic_chat dashboard quality score    | build | samagama       | 889085       | 12691         | 0.0  |
| ses_facb90534ffe1XtH6F8Gp09ykk | Copy image from Google Docs to clipboard          | build | samagama       | 152569       | 435           | 0.0  |
| ses_facd5a156ffeHh1mhyClcQPde7 | Hindi translation showing raw key on contact page | build | samagama       | 1099745      | 23989         | 0.0  |
+--------------------------------+---------------------------------------------------+-------+----------------+--------------+---------------+------+
```

**Live providers proof:**

```sql
SELECT id, name, api_type, api_url
FROM opencode.providers
WHERE api_url IS NOT NULL
ORDER BY id
LIMIT 6;
```

```text
+-----------+------------+----------+---------------------------------------+
| id        | name       | api_type | api_url                               |
+-----------+------------+----------+---------------------------------------+
| anthropic | Anthropic  | aisdk    | http://127.0.0.1:3456                 |
| badtheory | badtheory  | aisdk    | https://api.badtheorylabs.com/v1      |
| btl       | btl        | aisdk    | https://runtime.badtheorylabs.com/v1  |
| evomap    | evomap     | aisdk    | https://api.evomap.ai/v1              |
| hardeep   | hardeep    | aisdk    | https://samagama.in/platform/proxy/v1 |
| nvidiavim | nvidia vim | aisdk    | https://integrate.api.nvidia.com/v1   |
+-----------+------------+----------+---------------------------------------+
```

**Live single-session proof:**

```sql
SELECT id, title, agent, model_provider, cost, created, updated
FROM opencode.session(id => 'ses_fa97a98bcffeopz53rsAqRyg7H');
```

```text
+--------------------------------+----------------------------------------+-------+----------------+------+---------------+---------------+
| id                             | title                                  | agent | model_provider | cost | created       | updated       |
+--------------------------------+----------------------------------------+-------+----------------+------+---------------+---------------+
| ses_fa97a98bcffeopz53rsAqRyg7H | New session - 2026-08-31T06:32:58.435Z | build | samagama       | 0.0  | 1788157978435 | 1788159288400 |
+--------------------------------+----------------------------------------+-------+----------------+------+---------------+---------------+
```

## Implementation notes

- Uses Coral source-spec DSL v3 with the HTTP backend.
- `OPENCODE_URL` is a configurable variable with a local-server
  default of `http://127.0.0.1:14096`.
- Does not require authentication. Local unsecured `opencode serve`
  is the supported v0.1.0 mode.
- The `sessions` table pages through `cursor.next` automatically
  (`page_size` default 50, max 500, max 50 pages).
- `providers` and `saved_permissions` are returned without pagination.
- The `request` field on each provider (which may carry an `apiKey`)
  is intentionally excluded to avoid leaking credentials.
- Session `created` and `updated` are exposed as raw epoch
  milliseconds (`Int64`) rather than ISO 8601 strings.
- The per-message transcript endpoint (`GET /api/session/{id}/message`)
  is intentionally omitted: the opencode server does not project
  historical messages into its in-memory store until a session is
  loaded, so it would return an empty list for the historical
  sessions the `sessions` table enumerates.
- Directory-scoped endpoints (`/api/skill`, `/api/command`,
  `/api/reference`, `/api/project`, `/api/session/{id}/message`) are
  out of scope for v0.1.0 because they require a `location[directory]`
  query parameter that the Coral query surface cannot bind without
  bracket-encoding support.

## Limitations

- Requires a running `opencode serve` instance; the source does not
  start or manage the server.
- Only one opencode-server location is queried per call. The server
  defaults to its own current working directory when no `location`
  query parameter is supplied, which is reflected in the `providers`
  and `saved_permissions` tables.
- Password-protected opencode servers are not yet supported. Start
  `opencode serve` without `OPENCODE_SERVER_PASSWORD` for v0.1.0.
- Per-message transcripts are not exposed. Agents that need full
  message history should query the underlying SQLite store directly
  (out of scope for this HTTP-backed source).
- The source is read-only. It does not start, stop, fork, share, or
  delete sessions, nor does it manage providers or permission rules.
- WSL, Docker, or remote-machine deployments may require a different
  `OPENCODE_URL` (LAN IP, `host.docker.internal`, or a tunnel).
