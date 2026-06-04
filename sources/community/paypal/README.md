# PayPal Source

Query PayPal balances, transaction search summaries, invoices, and webhooks through Coral SQL.

## Summary

This source lets Coral query PayPal reporting balances, transaction-search metadata, invoice rows, and configured webhooks. It targets PayPal REST APIs with OAuth 2.0 bearer-token authentication and keeps mutating checkout, payout, refund, invoice-write, and webhook-write operations out of scope.

## Provider docs

- Get API credentials: https://docs.paypal.ai/get-started/how-to/use-rest-api/get-api-credentials
- REST API requests: https://docs.paypal.ai/developer/how-to/api/make-api-requests
- Balances: https://docs.paypal.ai/reference/api/rest/balances/list-all-balances
- Transactions: https://docs.paypal.ai/reference/api/rest/transactions/list-transactions
- Invoices: https://docs.paypal.ai/reference/api/rest/invoices/list-invoices
- Webhooks: https://docs.paypal.ai/reference/api/rest/webhooks/list-webhooks
- Apps, scopes, and credentials: https://docs.paypal.ai/developer/how-to/apps-scopes-credentials

## Authentication

PayPal REST APIs use OAuth 2.0 access tokens. Exchange your PayPal REST app client ID and secret for an access token, then add the source with that token.

Sandbox token example:

```bash
curl -s -u "$PAYPAL_CLIENT_ID:$PAYPAL_CLIENT_SECRET" \
  -H "Accept: application/json" \
  -H "Accept-Language: en_US" \
  -d "grant_type=client_credentials" \
  https://api-m.sandbox.paypal.com/v1/oauth2/token
```

Add the community source:

```bash
PAYPAL_BASE_URL=https://api-m.sandbox.paypal.com \
PAYPAL_ACCESS_TOKEN=... \
coral source add --file sources/community/paypal/manifest.yaml
```

For live PayPal, use `https://api-m.paypal.com` as `PAYPAL_BASE_URL` and a live access token created from live REST app credentials.

The access token must include permissions for the tables you want to query. For the first version, useful scopes include reporting/search read access for balances and transactions, invoicing for invoices, and applications/webhooks for webhooks. PayPal returns the scopes granted to the token in the token response.

## Request limits

This source performs live read-only PayPal API requests. It does not create, capture, refund, send, or mutate PayPal resources. PayPal access tokens expire, sandbox and live credentials are separate, and individual APIs can enforce provider-specific limits such as transaction-search date-window limits.

## Source shape

- `paypal.balances` returns a balance summary row from `GET /v1/reporting/balances`.
- `paypal.transaction_search` returns one transaction-search response row from `GET /v1/reporting/transactions`, preserving top-level metadata and the raw `transaction_details` array.
- `paypal.invoices` lists invoice rows from `GET /v2/invoicing/invoices`.
- `paypal.webhooks` lists app webhooks from `GET /v1/notifications/webhooks`.

## Source scope

- Targets PayPal REST APIs through `PAYPAL_BASE_URL`; sandbox is the default.
- Requires `PAYPAL_ACCESS_TOKEN` bearer authentication.
- `paypal.transaction_search` requires `start_date` and `end_date`.
- Transaction search preserves the top-level account number, returned date window, totals, links, and raw transaction detail array.
- `paypal.invoices` uses page pagination with `page` and `page_size`.
- `paypal.webhooks` is read-only and supports the optional PayPal `anchor_type` filter.

## Limitations

- The source does not perform the client-credentials token exchange itself. Generate a PayPal access token outside Coral and provide it as `PAYPAL_ACCESS_TOKEN`.
- PayPal access tokens expire. Refresh the token and re-add/update the source when needed.
- Checkout order creation/capture, payments capture/refund, payouts, subscriptions, invoice creation/update/send, webhook creation/update/delete, disputes, vault, and tracking endpoints are intentionally omitted.
- `paypal.transaction_search` returns one response row with the raw transaction detail array instead of one SQL row per transaction so top-level response metadata is preserved.
- PayPal enforces provider-specific transaction-search date-window limits. Keep validation ranges short.
- Some tables may return zero rows in a fresh sandbox account, depending on app scopes and sandbox data.

## Tables

### `paypal.balances`

Returns PayPal reporting balances.

```sql
SELECT account_id, as_of_time, last_refresh_time,
       primary_currency, total_balance_value, available_balance_value
FROM paypal.balances
LIMIT 1;
```

### `paypal.transaction_search`

Searches PayPal transaction reporting data for a required date window.

```sql
SELECT account_number, total_items, total_pages,
       first_transaction_id, first_transaction_status,
       first_transaction_amount_currency_code, first_transaction_amount_value
FROM paypal.transaction_search
WHERE start_date = '2026-05-20T00:00:00Z'
  AND end_date = '2026-06-04T00:00:00Z'
  AND fields = 'all'
  AND page_size = 5
LIMIT 1;
```

### `paypal.invoices`

Lists PayPal invoices visible to the access token.

```sql
SELECT id, status, invoice_number, currency_code, invoice_date, create_time
FROM paypal.invoices
LIMIT 10;
```

### `paypal.webhooks`

Lists webhooks configured for the PayPal app.

```sql
SELECT id, url, event_types
FROM paypal.webhooks
LIMIT 10;
```

## Live validation output

Run these checks after setting `PAYPAL_BASE_URL` and `PAYPAL_ACCESS_TOKEN`.

```bash
$ coral source lint sources/community/paypal/manifest.yaml
Manifest is valid
```

```bash
$ coral source add --file sources/community/paypal/manifest.yaml
Added source paypal

  PASS paypal connected successfully

    paypal (4 tables)
    - balances
    - invoices
    - transaction_search
    - webhooks
    Query tests
    1 declared - 1 passed - 0 failed

    PASS SELECT account_id, as_of_time, last_refresh_time FROM paypal.balances LIMIT 1
      1 row
```

```bash
$ coral source test paypal
  PASS paypal connected successfully

    paypal (4 tables)
    - balances
    - invoices
    - transaction_search
    - webhooks
    Query tests
    1 declared - 1 passed - 0 failed

    PASS SELECT account_id, as_of_time, last_refresh_time FROM paypal.balances LIMIT 1
      1 row
```

```sql
SELECT table_name
FROM coral.tables
WHERE schema_name = 'paypal'
ORDER BY table_name;
```

```text
+--------------------+
| table_name         |
+--------------------+
| balances           |
| invoices           |
| transaction_search |
| webhooks           |
+--------------------+
```

```sql
SELECT table_name, column_name, data_type
FROM coral.columns
WHERE schema_name = 'paypal'
ORDER BY table_name, ordinal_position;
```

```text
+--------------------+----------------------------------------+-----------+
| table_name         | column_name                            | data_type |
+--------------------+----------------------------------------+-----------+
| balances           | as_of_time_filter                      | Utf8      |
| balances           | currency_code_filter                   | Utf8      |
| balances           | account_id                             | Utf8      |
| balances           | as_of_time                             | Timestamp |
| balances           | last_refresh_time                      | Timestamp |
| balances           | balances                               | Json      |
| balances           | primary_currency                       | Utf8      |
| balances           | total_balance_currency_code            | Utf8      |
| balances           | total_balance_value                    | Utf8      |
| balances           | available_balance_value                | Utf8      |
| balances           | withheld_balance_value                 | Utf8      |
| invoices           | id                                     | Utf8      |
| invoices           | parent_id                              | Utf8      |
| invoices           | status                                 | Utf8      |
| invoices           | invoice_number                         | Utf8      |
| invoices           | currency_code                          | Utf8      |
| invoices           | invoice_date                           | Utf8      |
| invoices           | due_date                               | Utf8      |
| invoices           | create_time                            | Timestamp |
| invoices           | last_update_time                       | Timestamp |
| invoices           | detail                                 | Json      |
| invoices           | invoicer                               | Json      |
| invoices           | primary_recipients                     | Json      |
| invoices           | amount                                 | Json      |
| invoices           | due_amount                             | Json      |
| invoices           | links                                  | Json      |
| transaction_search | start_date                             | Utf8      |
| transaction_search | end_date                               | Utf8      |
| transaction_search | fields                                 | Utf8      |
| transaction_search | page_size                              | Int64     |
| transaction_search | page_filter                            | Int64     |
| transaction_search | transaction_id                         | Utf8      |
| transaction_search | transaction_status                     | Utf8      |
| transaction_search | transaction_type                       | Utf8      |
| transaction_search | transaction_currency                   | Utf8      |
| transaction_search | account_number                         | Utf8      |
| transaction_search | returned_start_date                    | Timestamp |
| transaction_search | returned_end_date                      | Timestamp |
| transaction_search | last_refreshed_datetime                | Timestamp |
| transaction_search | page                                   | Int64     |
| transaction_search | total_items                            | Int64     |
| transaction_search | total_pages                            | Int64     |
| transaction_search | transaction_details                    | Json      |
| transaction_search | links                                  | Json      |
| transaction_search | first_transaction_id                   | Utf8      |
| transaction_search | first_transaction_event_code           | Utf8      |
| transaction_search | first_transaction_status               | Utf8      |
| transaction_search | first_transaction_amount_currency_code | Utf8      |
| transaction_search | first_transaction_amount_value         | Utf8      |
| webhooks           | anchor_type                            | Utf8      |
| webhooks           | id                                     | Utf8      |
| webhooks           | url                                    | Utf8      |
| webhooks           | event_types                            | Json      |
| webhooks           | links                                  | Json      |
+--------------------+----------------------------------------+-----------+
```

```sql
SELECT key, kind, required
FROM coral.inputs
WHERE schema_name = 'paypal'
ORDER BY key;
```

```text
+---------------------+----------+----------+
| key                 | kind     | required |
+---------------------+----------+----------+
| PAYPAL_ACCESS_TOKEN | secret   | true     |
| PAYPAL_BASE_URL     | variable | false    |
+---------------------+----------+----------+
```

```sql
SELECT account_id, as_of_time, last_refresh_time,
       primary_currency, total_balance_value, available_balance_value
FROM paypal.balances
LIMIT 1;
```

```text
+---------------+------------+-------------------+------------------+---------------------+-------------------------+
| account_id    | as_of_time | last_refresh_time | primary_currency | total_balance_value | available_balance_value |
+---------------+------------+-------------------+------------------+---------------------+-------------------------+
| BUADSUQLH7WEC |            |                   | USD              | 5000.00             | 5000.00                 |
+---------------+------------+-------------------+------------------+---------------------+-------------------------+
```

```sql
SELECT account_number, total_items, total_pages,
       first_transaction_id, first_transaction_status,
       first_transaction_amount_currency_code, first_transaction_amount_value
FROM paypal.transaction_search
WHERE start_date = '2026-05-20T00:00:00Z'
  AND end_date = '2026-06-04T00:00:00Z'
  AND fields = 'all'
  AND page_size = 5
LIMIT 1;
```

```text
+----------------+-------------+-------------+----------------------+--------------------------+----------------------------------------+--------------------------------+
| account_number | total_items | total_pages | first_transaction_id | first_transaction_status | first_transaction_amount_currency_code | first_transaction_amount_value |
+----------------+-------------+-------------+----------------------+--------------------------+----------------------------------------+--------------------------------+
| BUADSUQLH7WEC  | 1           | 1           | 9CG326359F0639103    | S                        | USD                                    | 5000.00                        |
+----------------+-------------+-------------+----------------------+--------------------------+----------------------------------------+--------------------------------+
```

```sql
SELECT account_number, total_items, transaction_type, transaction_currency,
       first_transaction_event_code, first_transaction_amount_currency_code
FROM paypal.transaction_search
WHERE start_date = '2026-05-20T00:00:00Z'
  AND end_date = '2026-06-04T00:00:00Z'
  AND fields = 'all'
  AND page_size = 5
  AND transaction_type = 'T1900'
  AND transaction_currency = 'USD'
LIMIT 1;
```

```text
+----------------+-------------+------------------+----------------------+------------------------------+----------------------------------------+
| account_number | total_items | transaction_type | transaction_currency | first_transaction_event_code | first_transaction_amount_currency_code |
+----------------+-------------+------------------+----------------------+------------------------------+----------------------------------------+
| BUADSUQLH7WEC  | 1           | T1900            | USD                  | T1900                        | USD                                    |
+----------------+-------------+------------------+----------------------+------------------------------+----------------------------------------+
```

```sql
SELECT id, status, invoice_number, currency_code, invoice_date, create_time
FROM paypal.invoices
LIMIT 10;
```

```text
+----+--------+----------------+---------------+--------------+-------------+
| id | status | invoice_number | currency_code | invoice_date | create_time |
+----+--------+----------------+---------------+--------------+-------------+
+----+--------+----------------+---------------+--------------+-------------+
```

```sql
SELECT id, url, event_types
FROM paypal.webhooks
LIMIT 10;
```

```text
+----+-----+-------------+
| id | url | event_types |
+----+-----+-------------+
+----+-----+-------------+
```
