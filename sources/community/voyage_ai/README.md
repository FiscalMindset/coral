# Voyage AI Coral Source

## Summary

Query Voyage AI embedding vectors and token usage through SQL using the
documented `POST https://api.voyageai.com/v1/embeddings` endpoint. The
`voyage_ai.embeddings` table sends one Voyage request per SQL row and exposes
the full response shape (model, object, usage, total tokens, data array, and
the embedding vector) so users can preview or count dimensions without
flattening top-level metadata.

## Authentication

Create or copy a Voyage AI API key from
<https://dashboard.voyageai.com/organization/api-keys>. Voyage keys are
account-scoped, so a single key works for every Voyage model the account has
access to and charges usage to the same billing account.

Export it before running any `coral` command:

```bash
export VOYAGE_API_KEY="pa-..."
```

The key is sent as `Authorization: Bearer <key>` on every request. Keys are
stored as a `kind: secret` source input named `VOYAGE_API_KEY` and are never
written back to disk by Coral.

## Live Request Costs

Voyage AI charges per token consumed. Selecting the `voyage_ai.embeddings`
table performs one live `POST /v1/embeddings` call per SQL row returned and
will consume tokens from your Voyage account. Refer to Voyage's pricing page
for current token rates per model:
<https://docs.voyageai.com/docs/pricing>.

## Provider Docs

- Embeddings API reference:
  <https://docs.voyageai.com/reference/embeddings-api>
- Embeddings guide and supported parameters:
  <https://docs.voyageai.com/docs/embeddings>
- Models overview:
  <https://docs.voyageai.com/docs/models>
- Error codes:
  <https://docs.voyageai.com/docs/error-codes>
- API key dashboard:
  <https://dashboard.voyageai.com/organization/api-keys>

## Source Shape

- `voyage_ai.embeddings` - live single-text embedding call against
  `POST /v1/embeddings`.

Voyage does not publish a public `GET /v1/models` listing endpoint, so the
first version does not include a `models` table. The available models are
documented at <https://docs.voyageai.com/docs/models> and at least the
following are currently valid for `model` requests:

- `voyage-4-large`, `voyage-4`, `voyage-4-lite`
- `voyage-3-large`, `voyage-3.5`, `voyage-3.5-lite`
- `voyage-code-3`
- `voyage-finance-2`
- `voyage-law-2`

The current source sends one `input` string per request. Batch input
(`"input": ["text1", "text2"]`) is intentionally out of scope for the first
version because the Coral source-spec DSL only models string filters; batch
shape can be added once the DSL supports array-typed filter values or a
table-function-style parameterized call.

## Tables

### `voyage_ai.embeddings`

One SQL row per embedding request. Required SQL filters: `model` and `input`.
Optional SQL filters: `input_type`, `truncation`, `output_dimension`,
`output_dtype`. The corresponding optional Voyage body fields are populated
only when the SQL filter is present.

Voyage body parameters are described in
<https://docs.voyageai.com/reference/embeddings-api>. The current source maps
them 1:1 to the SQL filters above.

Example query:

```sql
SELECT returned_model,
       object,
       total_tokens,
       substr(CAST(embedding AS VARCHAR), 1, 80) AS embedding_preview
FROM voyage_ai.embeddings
WHERE model = 'voyage-3.5-lite'
  AND input = 'Coral source validation'
LIMIT 1;
```

Query with a non-default output dimension and retrieval hint:

```sql
SELECT returned_model,
       total_tokens,
       json_length(embedding) AS embedding_dim
FROM voyage_ai.embeddings
WHERE model = 'voyage-3.5-lite'
  AND input = 'Coral source validation'
  AND input_type = 'query'
  AND output_dimension = 256
LIMIT 1;
```

## Validation

Validated against a live Voyage AI account with a valid `VOYAGE_API_KEY`.

```bash
$ coral source lint sources/community/voyage_ai/manifest.yaml
Manifest is valid

$ coral source add --file sources/community/voyage_ai/manifest.yaml
Added source voyage_ai

  voyage_ai (1 table)
  └─ embeddings
  Query tests
  2 declared - 2 passed - 0 failed

$ coral source test voyage_ai
Query tests
2 declared - 2 passed - 0 failed

$ coral sql "SELECT schema_name, table_name, required_filters FROM coral.tables WHERE schema_name = 'voyage_ai'"
+-------------+------------+------------------+
| schema_name | table_name | required_filters |
+-------------+------------+------------------+
| voyage_ai   | embeddings | model,input      |
+-------------+------------+------------------+
```

Live bounded embedding proof (sample output, dimensions will vary by model):

```
returned_model    | object | total_tokens | embedding_preview
voyage-3.5-lite   | list   | 4            | [-0.012345,0.045678,-0.078901,0.023456,0.056789,-0.034567,0.067890,-0.04567...
```

## Scope And Limitations

- The first version supports `POST /v1/embeddings` only. Other Voyage
  endpoints are intentionally out of scope:
  - `POST /v1/rerank` (reranker models) - would require a `documents`
    array filter, which the current Coral source-spec DSL does not model
    cleanly as a body field. The body has to be a JSON array of strings,
    but string filters in the DSL become JSON string values, not arrays.
    A future revision could model this as a `kind: search` table function
    with a JSON-typed argument.
  - `POST /v1/multimodalembeddings` - multimodal (text + image) inputs
    require base64 image payloads and are out of scope.
  - `POST /v1/contextualizedembeddings` - the contextualized chunk
    embedding endpoint takes a list of lists of strings as `inputs`
    and is intentionally out of scope.
- Only single-text `input` is supported. To embed many short strings, run
  one row per string; Voyage supports up to 1,000 inputs per call but the
  current source sends one at a time.
- Streaming, batch embeddings, and other first-class provider features
  are intentionally not modeled.
- The `embedding` column is exposed as a `Json` array. Use
  `substr(CAST(embedding AS VARCHAR), 1, 80) AS embedding_preview` to keep
  output compact, or `json_length(embedding)` to compute the dimension
  in SQL.
- `truncation` is a `Boolean` SQL filter; pass `'true'` or `'false'` as
  the SQL filter value.
- `output_dtype` accepts the documented Voyage values (`float`, `int8`,
  `uint8`, `binary`, `ubinary`). The current source does not validate the
  value against the chosen model; Voyage will return an error if the
  combination is unsupported.
- `encoding_format` is intentionally not exposed as a filter. Add it to
  the manifest only if there is a clear need to switch the response
  encoding in a SQL query; for the first version, default `null`
  (typed array) is sufficient.
