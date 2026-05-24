# Groq AI Community Source

**Version:** 0.1.0
**Backend:** HTTP
**Tables:** 3
**Base URL:** `https://api.groq.com/openai/v1`

Query GroqCloud model metadata and run chat completions through Coral SQL. This community source is useful when you want to inspect available models or test prompts against Groq without leaving the SQL workflow.

## Install

Community sources are not bundled with the Coral binary. Add the manifest from this directory:

```bash
coral source add --file sources/community/groq_ai/manifest.yaml
```

Or copy `manifest.yaml` into your workspace and pass that path to `coral source add --file`.

## Authentication

Requires `GROQ_API_KEY`.

Create or copy a key from:
https://console.groq.com/keys

The key is sent as a bearer token to Groq's OpenAI-compatible API.

```bash
export GROQ_API_KEY="your_groq_api_key"
coral source add --file sources/community/groq_ai/manifest.yaml
```

## Table categories

| Table | Description |
| --- | --- |
| `models` | Active GroqCloud models returned by the Models API |
| `model` | Metadata for one Groq model ID |
| `chat_completions` | One chat completion request using SQL filters |

## Example queries

```sql
SELECT id, object, owned_by
FROM groq_ai.models
LIMIT 20;
```

```sql
SELECT id, object, owned_by, active, context_window
FROM groq_ai.model
WHERE model_id = 'llama-3.3-70b-versatile';
```

```sql
SELECT content, finish_reason
FROM groq_ai.chat_completions
WHERE model = 'llama-3.3-70b-versatile'
  AND prompt = 'What is Python?'
LIMIT 1;
```

## Validation

```bash
coral source lint sources/community/groq_ai/manifest.yaml
export GROQ_API_KEY=...
coral source add --file sources/community/groq_ai/manifest.yaml
coral source test groq_ai
```

## Limitations

- The `chat_completions` table performs an API call for each query.
- Keep prompts short and bounded for demos and tests.
- The table supports a single user message because it is meant to prove Coral can call Groq through SQL, not replace a full chat client.

## Contributing

Follow [CONTRIBUTING.md](../../../CONTRIBUTING.md), run `make lint-sources`, and include the validation steps you used in the PR description.
