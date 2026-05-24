# Groq AI community source

Query GroqCloud model metadata and run simple chat completions through Coral SQL.
This source adds Groq's OpenAI-compatible API to the community catalog so users
and agents can inspect available models, verify model configuration, and smoke
test prompts without leaving the Coral workflow.

**Version:** 0.1.0
**Backend:** HTTP
**Tables:** 3
**Base URL:** `https://api.groq.com/openai/v1`

## Why this source

Groq is a common inference provider for fast LLM experiments, agent prototypes,
and production chat workloads. Coral did not have a Groq source yet, so this
community spec gives the reef a focused read/query surface for:

- Discovering active GroqCloud models from SQL.
- Looking up metadata for one model before using it in an agent or workflow.
- Running a bounded chat-completion prompt as an integration smoke test.
- Joining model metadata with other Coral sources in local analysis workflows.

The v1 surface is intentionally narrow and read-oriented. It proves Coral can
authenticate against Groq, call Groq's OpenAI-compatible endpoints, map JSON
responses into tables, and validate the source with declared test queries.

## Installation

Community sources are not bundled with the Coral binary. Clone the Coral
repository and add the manifest from this directory:

```bash
coral source add --file sources/community/groq_ai/manifest.yaml
```

You can also copy `manifest.yaml` into another workspace and pass that path to
`coral source add --file`.

## Authentication

Create or copy an API key from the GroqCloud console:

https://console.groq.com/keys

Set the key as `GROQ_API_KEY` before adding or testing the source. Coral sends
it as a bearer token to Groq's OpenAI-compatible API.

```bash
export GROQ_API_KEY="your_groq_api_key"
coral source add --file sources/community/groq_ai/manifest.yaml
```

Interactive install also works:

```bash
coral source add --interactive --file sources/community/groq_ai/manifest.yaml
```

## Tables

| Table | Description | Required filters |
| --- | --- | --- |
| `groq_ai.models` | Active GroqCloud models returned by the Models API. | None |
| `groq_ai.model` | Metadata for one Groq model ID. | `model_id` |
| `groq_ai.chat_completions` | Run one chat completion request using SQL filters. | `model`, `prompt` |

### `groq_ai.models`

Lists models available from `GET /models`.

```sql
SELECT id, object, owned_by, active, context_window
FROM groq_ai.models
LIMIT 20;
```

### `groq_ai.model`

Fetches metadata for one model from `GET /models/{model_id}`.

```sql
SELECT id, object, owned_by, active, context_window
FROM groq_ai.model
WHERE model_id = 'llama-3.3-70b-versatile';
```

### `groq_ai.chat_completions`

Runs a single user-message chat completion through `POST /chat/completions`.
Use `max_tokens` when you want to keep validation output small.

```sql
SELECT content, finish_reason
FROM groq_ai.chat_completions
WHERE model = 'llama-3.3-70b-versatile'
  AND prompt = 'What is Python? Reply in one short line under 15 words.'
  AND max_tokens = 40
LIMIT 1;
```

## Validation

Run the source-level checks before opening or updating a PR:

```bash
coral source lint sources/community/groq_ai/manifest.yaml

export GROQ_API_KEY="your_groq_api_key"
coral source add --file sources/community/groq_ai/manifest.yaml
coral source test groq_ai
```

The declared test queries cover model discovery and two chat-completion smoke
tests:

```sql
SELECT * FROM groq_ai.models LIMIT 5;

SELECT content
FROM groq_ai.chat_completions
WHERE model = 'llama-3.3-70b-versatile'
  AND prompt = 'Reply with exactly: Coral Groq works'
LIMIT 1;

SELECT content
FROM groq_ai.chat_completions
WHERE model = 'llama-3.3-70b-versatile'
  AND prompt = 'What is Python?'
LIMIT 1;
```

For PR proof, the local verification script used for this contribution is:

```powershell
coral-forge-agent\scripts\groq_ai_pr_proof.ps1
```

Screenshots from that proof run are stored under:

```text
output_proof/groq_ai
```

## Implementation notes

- Uses Coral source-spec DSL v3 with the HTTP backend.
- Uses `HeaderAuth` with `Authorization: Bearer {{input.GROQ_API_KEY}}`.
- Maps Groq's `data` array from `GET /models` into `groq_ai.models`.
- Maps `choices[*].message.content` from `POST /chat/completions` into
  `groq_ai.chat_completions.content`.
- Echoes required SQL filters such as `model`, `prompt`, and `model_id` back as
  virtual columns so query results keep their request context.
- Does not require runtime, CLI, MCP, or UI changes.

## Limitations

- This source is read/query oriented and does not manage Groq account settings.
- `chat_completions` performs a live API call for each query.
- The chat table supports one user message per query. It is intended for
  validation and lightweight SQL workflows, not as a full chat client.
- Responses, available models, rate limits, and errors depend on the Groq
  account, API key permissions, and the selected model.

## Contributing

Follow [CONTRIBUTING.md](../../../CONTRIBUTING.md), keep the manifest focused,
and include the validation commands plus proof output in the PR description.
