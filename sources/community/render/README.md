# Render

**Version:** 0.1.0
**Backend:** HTTP
**Tables:** 3

Query services, deploys, and workspaces from Render. Monitor deployment status, service configuration, and infrastructure through SQL.

## Installation

Install the source via the CLI:

```bash
coral source add --file sources/community/render/manifest.yaml
```

## Credentials

To use this source, you will need a Render API key.

1. Log in to [Render](https://dashboard.render.com).
2. Navigate to [Account Settings > API Keys](https://dashboard.render.com/u/settings#api-keys).
3. Create an API key (starts with `rnd_`).
4. Provide it when prompted by `coral source add` or set it as an environment variable:

```bash
export RENDER_API_KEY="rnd_your-api-key"
```

## Quick Start

```sql
-- List services (one page, up to 100 rows; use cursor filter for more)
SELECT service_id, name, type, status, url
FROM render.services;

-- List deploys for a service
SELECT deploy_id, status, trigger, commit_message
FROM render.deploys
WHERE service_id = 'srv-your-service-id'
LIMIT 10;

-- List workspaces
SELECT owner_id, name, email, type
FROM render.workspaces;

-- Find services by type
SELECT service_id, name, url
FROM render.services
WHERE type = 'web_service';
```

## Tables

### `services`

Services deployed on Render. Includes static sites, web services, private services, background workers, and cron jobs. No required filters.

**Filters**

| Filter | Type | Required | Description |
|--------|------|----------|-------------|
| `type` | Utf8 | | Filter by service type (static_site, web_service, private_service, background_worker, cron_job) |
| `cursor` | Utf8 | | Cursor from a previous query for manual pagination |

**Columns**

| Column | Type | Description |
|--------|------|-------------|
| `cursor` | Utf8 | Pagination cursor for manual pagination |
| `service_id` | Utf8 | Unique identifier for the service |
| `name` | Utf8 | Name of the service |
| `type` | Utf8 | Service type (static_site, web_service, private_service, background_worker, cron_job) |
| `status` | Utf8 | Suspension status of the service (not_suspended, suspended) |
| `repo` | Utf8 | Git repository URL |
| `branch` | Utf8 | Git branch used for deployments |
| `auto_deploy` | Utf8 | Whether auto-deploy is enabled (yes/no) |
| `url` | Utf8 | URL of the service (private services return a non-public internal URL) |
| `dashboard_url` | Utf8 | URL to the Render dashboard |
| `owner_id` | Utf8 | ID of the owner (user or team) |
| `slug` | Utf8 | URL slug of the service |
| `created_at` | Timestamp | When the service was created (ISO 8601) |
| `updated_at` | Timestamp | When the service was last updated (ISO 8601) |

---

### `deploys`

Deployment history for a Render service. Includes commit info, status, trigger, and timing. Requires `service_id` filter.

**Filters**

| Filter | Type | Required | Description |
|--------|------|----------|-------------|
| `service_id` | Utf8 | Yes | ID of the service to list deploys for |
| `status` | Utf8 | | Filter by deploy status (created, queued, build_in_progress, update_in_progress, live, deactivated, build_failed, update_failed, canceled, pre_deploy_in_progress, pre_deploy_failed) |
| `cursor` | Utf8 | | Cursor from a previous query for manual pagination |

**Columns**

| Column | Type | Description |
|--------|------|-------------|
| `cursor` | Utf8 | Pagination cursor for manual pagination |
| `service_id` | Utf8 | ID of the service (populated from filter via `from_filter`) |
| `deploy_id` | Utf8 | Unique identifier for the deploy |
| `status` | Utf8 | Deploy status (created, queued, build_in_progress, update_in_progress, live, deactivated, build_failed, update_failed, canceled, pre_deploy_in_progress, pre_deploy_failed) |
| `trigger` | Utf8 | What triggered the deploy (api, blueprint_sync, deploy_hook, deployed_by_render, manual, other, new_commit, rollback, service_resumed, service_updated) |
| `commit_id` | Utf8 | Git commit SHA |
| `commit_message` | Utf8 | Git commit message |
| `commit_created_at` | Timestamp | When the commit was created (ISO 8601) |
| `created_at` | Timestamp | When the deploy was created (ISO 8601) |
| `started_at` | Timestamp | When the deploy started (ISO 8601) |
| `finished_at` | Timestamp | When the deploy finished (ISO 8601) |
| `updated_at` | Timestamp | When the deploy was last updated (ISO 8601) |

---

### `workspaces`

Workspaces the API key has access to. The key grants access to every workspace the user belongs to. No required filters.

**Filters**

| Filter | Type | Required | Description |
|--------|------|----------|-------------|
| `cursor` | Utf8 | | Cursor from a previous query for manual pagination |

**Columns**

| Column | Type | Description |
|--------|------|-------------|
| `cursor` | Utf8 | Pagination cursor for manual pagination |
| `owner_id` | Utf8 | Unique identifier for the workspace |
| `name` | Utf8 | Name of the workspace |
| `email` | Utf8 | Email address of the workspace owner |
| `type` | Utf8 | Workspace type (user or team) |

## Source scope

- Targets the Render API at `https://api.render.com/v1`.
- Requires `RENDER_API_KEY` authentication as a Bearer token.
- `deploys` requires a `service_id` filter (URL path segment). Use `services` to discover service IDs.
- SQL `LIMIT` is pushed to the API via `limit` query param (default 20, max 100).
- Render's API wraps each item in a `{cursor, entity}` object — columns extract from the nested entity.
- 1 declared test query (`services`) is source-independent.
- Provides read-only access. Creating, updating, or deleting services and deploys is out of scope.

## Limitations

- The source provides read-only list access only. Service creation, deployment triggers, environment variable management, and other write operations are out of scope.
- Render uses per-item cursor pagination. Each row includes a `cursor` column. To retrieve another page, pass the last row's cursor to a new query: `WHERE cursor = 'last_cursor_value'`.
- Timestamp fields use `Timestamp` type — Render returns RFC3339 strings with timezone (`Z` suffix) which Coral parses natively.
- The `url` column in `services` is extracted from `serviceDetails.url`. Private services return a non-public internal URL. Some service types may have null URLs.
- The `service_id` column in `deploys` is populated from the required filter via `from_filter` expression.

## Provider docs

- Render API reference: https://api-docs.render.com
- Services API: https://api-docs.render.com/reference/list-services
- Deploys API: https://api-docs.render.com/reference/list-deploys
- Workspaces API: https://api-docs.render.com/reference/list-owners
- API keys: https://dashboard.render.com/u/settings#api-keys

## Live validation output

Validated against a live Render account with a valid `RENDER_API_KEY`.

```bash
$ coral source lint sources/community/render/manifest.yaml
Manifest is valid
```

```bash
$ coral source add --file sources/community/render/manifest.yaml
Added source render

  ✓ render connected successfully

    render (3 tables)
    ├─ deploys
    ├─ workspaces
    └─ services
    Query tests
    1 declared · 1 passed · 0 failed

    ✓ SELECT service_id, name, type, status FROM render.services LIMIT 3
      3 rows
```

**Table introspection:**

```sql
SELECT table_name, description, required_filters
FROM coral.tables
WHERE schema_name = 'render'
ORDER BY table_name;
```

```text
+------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------------+------------------+
| table_name | description                                                                                                                                                       | required_filters |
+------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------------+------------------+
| deploys    | Deployment history for a Render service. Includes commit info, status, trigger, and timing for each deploy.                                                       | service_id       |
| services   | Services deployed on Render. Includes static sites, web services, private services, background workers, and cron jobs with their configuration, status, and URLs. |                  |
| workspaces | Workspaces the API key has access to. The key grants access to every workspace the user belongs to.                                                               |                  |
+------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------------+------------------+
```

**Live services proof:**

```sql
SELECT service_id, name, type, status, url
FROM render.services LIMIT 3;
```

```text
+--------------------------+--------------------+-------------+---------------+-----------------------------------------+
| service_id               | name               | type        | status        | url                                     |
+--------------------------+--------------------+-------------+---------------+-----------------------------------------+
| srv-d8lsuubeo5us738b7k7g | vicky              | static_site | not_suspended | https://vicky-4sjs.onrender.com         |
| srv-d8lsufbeo5us738b756g | algsochvicky       | static_site | not_suspended | https://algsochvicky-h2rq.onrender.com  |
| srv-d8k7kicvikkc73buknb0 | polybazar-frontend | web_service | not_suspended | https://polybazar-frontend.onrender.com |
+--------------------------+--------------------+-------------+---------------+-----------------------------------------+
```

**Live type filter proof:**

```sql
SELECT service_id, name, url
FROM render.services
WHERE type = 'web_service'
LIMIT 3;
```

```text
+--------------------------+--------------------+-----------------------------------------+
| service_id               | name               | url                                     |
+--------------------------+--------------------+-----------------------------------------+
| srv-d8k7kicvikkc73buknb0 | polybazar-frontend | https://polybazar-frontend.onrender.com |
| srv-d8i03htckfvc73b98a4g | Kairon-2           | https://kairon-2.onrender.com           |
| srv-d848fkv7f7vs739s6i20 | Kairon             | https://kairon-3.onrender.com           |
+--------------------------+--------------------+-----------------------------------------+
```

**Live deploys proof:**

```sql
SELECT deploy_id, status, trigger
FROM render.deploys
WHERE service_id = 'srv-d8k7kicvikkc73buknb0'
LIMIT 3;
```

```text
+--------------------------+--------------+------------+
| deploy_id                | status       | trigger    |
+--------------------------+--------------+------------+
| dep-d8k7vhgg4nts73fplo2g | build_failed | manual     |
| dep-d8k7vda8qa3s7389vupg | canceled     | new_commit |
| dep-d8k7qmbtqb8s7391cbr0 | build_failed | manual     |
+--------------------------+--------------+------------+
```

**Live deploy status filter proof:**

```sql
SELECT deploy_id, status, trigger
FROM render.deploys
WHERE service_id = 'srv-d8k7kicvikkc73buknb0'
AND status = 'build_failed'
LIMIT 3;
```

```text
+--------------------------+--------------+---------+
| deploy_id                | status       | trigger |
+--------------------------+--------------+---------+
| dep-d8k7vhgg4nts73fplo2g | build_failed | manual  |
| dep-d8k7qmbtqb8s7391cbr0 | build_failed | manual  |
| dep-d8k7kisvikkc73buknqg | build_failed | manual  |
+--------------------------+--------------+---------+
```

**Live workspaces proof:**

```sql
SELECT owner_id, name, email, type
FROM render.workspaces;
```

```text
+--------------------------+---------+----------------------+------+
| owner_id                 | name    | email                | type |
+--------------------------+---------+----------------------+------+
| tea-cvrsaomr433s73b3f8ag | algsoch | npdimagine@gmail.com | team |
+--------------------------+---------+----------------------+------+
```
