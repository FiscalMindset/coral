# Render

**Version:** 0.1.0
**Backend:** HTTP
**Tables:** 3

Query services, deploys, and owners from Render. Monitor deployment status, service configuration, and infrastructure through SQL.

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
-- List all services
SELECT service_id, name, type, status, url
FROM render.services;

-- List deploys for a service
SELECT deploy_id, status, trigger, commit_message
FROM render.deploys
WHERE service_id = 'srv-your-service-id'
LIMIT 10;

-- Check service owners
SELECT owner_id, name, email, type
FROM render.owners;

-- Find services by type
SELECT service_id, name, url
FROM render.services
WHERE type = 'web_service';
```

## Tables

### `services`

Services deployed on Render. Includes static sites, web services, private services, background workers, and cron jobs. No required filters.

**Columns**

| Column | Type | Description |
|--------|------|-------------|
| `service_id` | Utf8 | Unique identifier for the service |
| `name` | Utf8 | Name of the service |
| `type` | Utf8 | Service type (static_site, web_service, private_service, background_worker, cron_job) |
| `status` | Utf8 | Suspension status of the service |
| `repo` | Utf8 | Git repository URL |
| `branch` | Utf8 | Git branch used for deployments |
| `auto_deploy` | Utf8 | Whether auto-deploy is enabled (yes/no) |
| `url` | Utf8 | Public URL of the service |
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

**Columns**

| Column | Type | Description |
|--------|------|-------------|
| `service_id` | Utf8 | ID of the service (populated from filter via `from_filter`) |
| `deploy_id` | Utf8 | Unique identifier for the deploy |
| `status` | Utf8 | Deploy status (live, deactivated, build_failed, update_failed, canceled, pre_deploy_in_progress, pre_deploy_failed) |
| `trigger` | Utf8 | What triggered the deploy (new_commit, manual, api) |
| `commit_id` | Utf8 | Git commit SHA |
| `commit_message` | Utf8 | Git commit message |
| `commit_created_at` | Timestamp | When the commit was created (ISO 8601) |
| `created_at` | Timestamp | When the deploy was created (ISO 8601) |
| `started_at` | Timestamp | When the deploy started (ISO 8601) |
| `finished_at` | Timestamp | When the deploy finished (ISO 8601) |
| `updated_at` | Timestamp | When the deploy was last updated (ISO 8601) |

---

### `owners`

Owners (users and teams) associated with your Render account. No required filters.

**Columns**

| Column | Type | Description |
|--------|------|-------------|
| `owner_id` | Utf8 | Unique identifier for the owner |
| `name` | Utf8 | Name of the owner |
| `email` | Utf8 | Email address of the owner |
| `type` | Utf8 | Owner type (user or team) |

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
- Render uses per-item cursor pagination. Each row includes a `cursor` column. For accounts with >100 items, pass the last row's cursor to the `cursor` filter for manual pagination: `WHERE cursor = 'last_cursor_value'`.
- Timestamp fields use `Timestamp` type — Render returns RFC3339 strings with timezone (`Z` suffix) which Coral parses natively.
- The `url` column in `services` is extracted from `serviceDetails.url` which is only present for web services and static sites. Other service types may have null URLs.
- The `service_id` column in `deploys` is populated from the required filter via `from_filter` expression.

## Provider docs

- Render API reference: https://docs.render.com/api
- Services API: https://docs.render.com/api/rest-api#services
- Deploys API: https://docs.render.com/api/rest-api#deploys
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
    ├─ owners
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
+------------+--------------------------------------------------------------------------------------------------------------+------------------+
| table_name | description                                                                                                  | required_filters |
+------------+--------------------------------------------------------------------------------------------------------------+------------------+
| deploys    | Deployment history for a Render service. Includes commit info, status, trigger, and timing for each deploy. | service_id       |
| owners     | Owners (users and teams) associated with your Render account.                                                |                  |
| services   | Services deployed on Render. Includes static sites, web services, private services, ...                     |                  |
+------------+--------------------------------------------------------------------------------------------------------------+------------------+
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
| srv-0000000000000000000g | user-site          | static_site | not_suspended | https://user-site.onrender.com          |
| srv-0000000000000000000g | user-app           | static_site | not_suspended | https://user-app.onrender.com           |
| srv-0000000000000000000g | user-frontend      | web_service | not_suspended | https://user-frontend.onrender.com      |
+--------------------------+--------------------+-------------+---------------+-----------------------------------------+
```

**Live deploys proof:**

```sql
SELECT deploy_id, status, trigger
FROM render.deploys
WHERE service_id = 'srv-0000000000000000000g'
LIMIT 3;
```

```text
+--------------------------+-------------+------------+
| deploy_id                | status      | trigger    |
+--------------------------+-------------+------------+
| dep-0000000000000000000g | live        | new_commit |
| dep-0000000000000000000g | deactivated | new_commit |
| dep-0000000000000000000g | deactivated | new_commit |
+--------------------------+-------------+------------+
```

**Live owners proof:**

```sql
SELECT owner_id, name, email, type
FROM render.owners;
```

```text
+--------------------------+---------+-----------------------+------+
| owner_id                 | name    | email                 | type |
+--------------------------+---------+-----------------------+------+
| tea-0000000000000000000g | user    | user@example.com      | team |
+--------------------------+---------+-----------------------+------+
```
