# Deepgram community source

Query Deepgram speech-to-text model metadata and run audio transcriptions through
Coral SQL. This source exposes available STT models and a live transcription table
that accepts an audio URL and model name, returning transcript text, confidence
scores, word-level timing, and usage metadata.

**Version:** 0.1.0
**Backend:** HTTP
**Tables:** 2
**Base URL:** `https://api.deepgram.com`

## Why this source

Deepgram is a speech-to-text API provider offering both batch and streaming
transcription with features like diarization, sentiment analysis, and topic
extraction. Coral did not have a Deepgram source yet, so this community spec
gives users a focused read/query surface for:

- Discovering available Deepgram STT models from SQL.
- Running bounded transcription queries against publicly accessible audio URLs.
- Extracting word-level timing, confidence scores, and usage metadata.
- Joining model metadata with other Coral sources in local analysis workflows.

The v1 surface is intentionally narrow and read-oriented. It proves Coral can
authenticate against Deepgram, call the transcription API, map JSON responses
into tables, and validate the source with declared test queries.

## Installation

Community sources are not bundled with the Coral binary. Clone the Coral
repository and add the manifest from this directory:

```bash
coral source add --file sources/community/deepgram/manifest.yaml
```

You can also copy `manifest.yaml` into another workspace and pass that path to
`coral source add --file`.

## Authentication

Create or copy an API key from the Deepgram console:

https://console.deepgram.com/

Set the key as `DEEPGRAM_API_KEY` before adding or testing the source. Coral sends
it as a `Token` header to Deepgram's API (not Bearer).

```bash
export DEEPGRAM_API_KEY="your_deepgram_api_key"
coral source add --file sources/community/deepgram/manifest.yaml
```

Interactive install also works:

```bash
coral source add --interactive --file sources/community/deepgram/manifest.yaml
```

## Provider docs

- Deepgram API reference: https://developers.deepgram.com/
- Deepgram models: https://console.deepgram.com/
- Deepgram listen endpoint: https://developers.deepgram.com/reference/listen

## Tables

| Table | Description | Required filters |
| --- | --- | --- |
| `deepgram.models` | Available Deepgram STT models from the Models API. | None |
| `deepgram.transcriptions` | Run one transcription request against an audio URL. | `model`, `url` |

### `deepgram.models`

Lists available STT models from `GET /v1/models`.

```sql
SELECT name, architecture, version, languages
FROM deepgram.models
WHERE architecture = 'polaris'
LIMIT 10;
```

### `deepgram.transcriptions`

Runs a single transcription through `POST /v1/listen`. The audio URL must be
publicly accessible. Use the `general` or `nova-2` model for most workloads.

```sql
SELECT transcript, confidence, duration, characters
FROM deepgram.transcriptions
WHERE model = 'nova-2'
  AND url = 'https://example.com/audio.wav'
LIMIT 1;
```

Enable optional features via filters:

```sql
SELECT transcript, sentiment, topics
FROM deepgram.transcriptions
WHERE model = 'nova-2'
  AND url = 'https://example.com/audio.wav'
  AND punctuate = true
  AND smart_format = true
  AND sentiment = true
LIMIT 1;
```

## Validation

```bash
$ coral source lint sources/community/deepgram/manifest.yaml
Manifest is valid
```

```bash
$ coral source add --file sources/community/deepgram/manifest.yaml
Added source deepgram

  PASS deepgram connected successfully

    deepgram (2 tables)
    - models
    - transcriptions
    Query tests
    2 declared - 2 passed - 0 failed

    PASS SELECT name, architecture, version FROM deepgram.models LIMIT 5
      5 rows

    PASS SELECT name, canonical_name, languages FROM deepgram.models WHERE architecture = 'polaris' LIMIT 5
      5 rows
```

```bash
$ coral source test deepgram
  PASS deepgram connected successfully

    deepgram (2 tables)
    - models
    - transcriptions
    Query tests
    2 declared - 2 passed - 0 failed

    PASS SELECT name, architecture, version FROM deepgram.models LIMIT 5
      5 rows

    PASS SELECT name, canonical_name, languages FROM deepgram.models WHERE architecture = 'polaris' LIMIT 5
      5 rows
```

```sql
SELECT table_name, description, required_filters
FROM coral.tables
WHERE schema_name = 'deepgram'
ORDER BY table_name;
```

```text
+----------------+---------------------------------------------------------------------------------------------------------------------------------------------+------------------+
| table_name     | description                                                                                                                                 | required_filters |
+----------------+---------------------------------------------------------------------------------------------------------------------------------------------+------------------+
| models         | Available Deepgram speech-to-text models from GET /v1/models.                                                                               |                  |
| transcriptions | Transcribe audio from a URL using Deepgram `POST /v1/listen`. One SQL row per transcription request; preserves top-level response metadata. | model,url        |
+----------------+---------------------------------------------------------------------------------------------------------------------------------------------+------------------+
```

```sql
SELECT column_name, data_type, is_virtual, is_required_filter
FROM coral.columns
WHERE schema_name = 'deepgram' AND table_name = 'models'
ORDER BY ordinal_position;
```

```text
+------------------+-----------+------------+--------------------+
| column_name      | data_type | is_virtual | is_required_filter |
+------------------+-----------+------------+--------------------+
| name             | Utf8      | false      | false              |
| canonical_name   | Utf8      | false      | false              |
| architecture     | Utf8      | false      | false              |
| languages        | Json      | false      | false              |
| version          | Utf8      | false      | false              |
| uuid             | Utf8      | false      | false              |
| batch            | Boolean   | false      | false              |
| streaming        | Boolean   | false      | false              |
| formatted_output | Boolean   | false      | false              |
| multilingual     | Boolean   | false      | false              |
+------------------+-----------+------------+--------------------+
```

```sql
SELECT column_name, data_type, is_virtual, is_required_filter
FROM coral.columns
WHERE schema_name = 'deepgram' AND table_name = 'transcriptions'
ORDER BY ordinal_position;
```

```text
+----------------------+-----------+------------+--------------------+
| column_name          | data_type | is_virtual | is_required_filter |
+----------------------+-----------+------------+--------------------+
| model                | Utf8      | true       | true               |
| url                  | Utf8      | true       | true               |
| language             | Utf8      | true       | false              |
| request_id           | Utf8      | false      | false              |
| encoding             | Utf8      | false      | false              |
| channels             | Int64     | false      | false              |
| sample_rate          | Int64     | false      | false              |
| duration             | Float64   | false      | false              |
| transcript           | Utf8      | false      | false              |
| confidence           | Float64   | false      | false              |
| words                | Json      | false      | false              |
| paragraphs           | Json      | false      | false              |
| summaries            | Json      | false      | false              |
| topics               | Json      | false      | false              |
| intent               | Utf8      | false      | false              |
| sentiment            | Utf8      | false      | false              |
| usage                | Json      | false      | false              |
| characters           | Int64     | false      | false              |
| total_audio_duration | Float64   | false      | false              |
+----------------------+-----------+------------+--------------------+
```

```sql
SELECT key, kind, required, is_set
FROM coral.inputs
WHERE schema_name = 'deepgram'
ORDER BY key;
```

```text
+------------------+--------+----------+--------+
| key              | kind   | required | is_set |
+------------------+--------+----------+--------+
| DEEPGRAM_API_KEY | secret | true     | true   |
+------------------+--------+----------+--------+
```

```sql
SELECT name, architecture, version, languages
FROM deepgram.models
LIMIT 10;
```

```text
+------------------+--------------+------------------+----------------+
| name             | architecture | version          | languages      |
+------------------+--------------+------------------+----------------+
| conversationalai | base         | 2021-11-10.1     | ["en","en-US"] |
| automotive       | polaris      | 1983-02-23.4285  | ["en","en-US"] |
| drivethru        | polaris      | 1983-05-08.23433 | ["en","en-US"] |
| finance          | polaris      | 2022-07-27.30495 | ["en","en-US"] |
| general          | polaris      | 2023-11-14.0     | ["taq"]        |
| general          | polaris      | 2023-07-13.28732 | ["en","en-US"] |
| general          | polaris      | 2022-12-08.27973 | ["pt-PT"]      |
| general          | polaris      | 2022-12-08.27925 | ["pt-BR"]      |
| general          | polaris      | 2022-12-08.27689 | ["pt"]         |
| general          | polaris      | 2022-12-08.24015 | ["de"]         |
+------------------+--------------+------------------+----------------+
```

```sql
SELECT architecture, count(*) AS model_count
FROM deepgram.models
GROUP BY architecture
ORDER BY model_count DESC;
```

```text
+--------------+-------------+
| architecture | model_count |
+--------------+-------------+
| nova-2       | 147         |
| nova-3       | 124         |
| base         | 90          |
| polaris      | 27          |
| whisper      | 9           |
| nova         | 9           |
| unknown      | 2           |
+--------------+-------------+
```

## Validation screenshots

![Deepgram validation 1 - lint](https://raw.githubusercontent.com/FiscalMindset/coral/deepgram-proof-assets/proof/deepgram/1_lint.png)

![Deepgram validation 2 - add source](https://raw.githubusercontent.com/FiscalMindset/coral/deepgram-proof-assets/proof/deepgram/2_add.png)

![Deepgram validation 3 - source test](https://raw.githubusercontent.com/FiscalMindset/coral/deepgram-proof-assets/proof/deepgram/3_source_test.png)

![Deepgram validation 4 - tables](https://raw.githubusercontent.com/FiscalMindset/coral/deepgram-proof-assets/proof/deepgram/4_tables.png)

![Deepgram validation 5 - columns models](https://raw.githubusercontent.com/FiscalMindset/coral/deepgram-proof-assets/proof/deepgram/5_columns_models.png)

![Deepgram validation 6 - columns transcriptions](https://raw.githubusercontent.com/FiscalMindset/coral/deepgram-proof-assets/proof/deepgram/6_columns_transcriptions.png)

![Deepgram validation 7 - inputs](https://raw.githubusercontent.com/FiscalMindset/coral/deepgram-proof-assets/proof/deepgram/7_inputs.png)

![Deepgram validation 8 - models main](https://raw.githubusercontent.com/FiscalMindset/coral/deepgram-proof-assets/proof/deepgram/8_models_main.png)

![Deepgram validation 9 - models polaris](https://raw.githubusercontent.com/FiscalMindset/coral/deepgram-proof-assets/proof/deepgram/9_models_polaris.png)

![Deepgram validation 10 - models group by](https://raw.githubusercontent.com/FiscalMindset/coral/deepgram-proof-assets/proof/deepgram/10_models_group_by.png)

![Deepgram validation 11 - models nova-2](https://raw.githubusercontent.com/FiscalMindset/coral/deepgram-proof-assets/proof/deepgram/11_models_nova2.png)

## Implementation notes

- Uses Coral source-spec DSL v3 with the HTTP backend.
- Uses `HeaderAuth` with `Authorization: Token {{input.DEEPGRAM_API_KEY}}`.
- Maps Deepgram's `stt` array from `GET /v1/models` into `deepgram.models`.
- Maps transcription response onto `deepgram.transcriptions`, including
  `results.channels.[0].alternatives.[0]` fields for transcript and metadata.
- Sets `fetch_limit_default: 1` on `transcriptions` to prevent accidental API calls.
- Requires `model` and `url` filters on `transcriptions`; audio URL must be publicly accessible.
- Does not require runtime, CLI, MCP, or UI changes.

## Limitations

- This source is read/query oriented and does not manage Deepgram account settings.
- `transcriptions` performs a live API call for each query and consumes transcription credits.
- The table requires a publicly accessible audio URL; private URLs or localhost will fail.
- Streaming transcription, custom language models (NLU), and webhook callbacks are not included.
- Responses, available models, pricing, rate limits, and errors depend on the Deepgram
  account, API key permissions, selected model, and current provider limits.

## Contributing

Follow [CONTRIBUTING.md](../../../CONTRIBUTING.md), keep the manifest focused,
and include the validation commands plus proof output in the PR description.