# Provider Health

Provider health checks verify whether expected environment variables are configured.

They do not call external APIs and do not print secret values.

## CLI

```powershell
uv run rld provider-health
```

Example shape:

```json
{
  "providers": {
    "openai": { "status": "configured" },
    "anthropic": { "status": "configured" },
    "google": { "status": "configured" },
    "huggingface": { "status": "configured" },
    "pypi": { "status": "configured" },
    "supabase": { "status": "configured" }
  },
  "configured_count": 6,
  "total_count": 6
}
```

## REST

Start the local API:

```powershell
uv run rld serve --host 127.0.0.1 --port 8787
```

Check providers:

```powershell
curl http://127.0.0.1:8787/health/providers
```

## Notes

- OpenAI requires `OPENAI_API_KEY`.
- Anthropic requires `ANTHROPIC_API_KEY`.
- Google requires `GOOGLE_API_KEY`.
- Hugging Face requires `HF_TOKEN`.
- PyPI publishing requires `PYPI_API_TOKEN`.
- Supabase requires `SUPABASE_URL` and at least one Supabase key.

Supported Supabase key names:

```text
SUPABASE_PUBLISHABLE_KEY
SUPABASE_ANON_KEY
SUPABASE_SECRET_KEY
SUPABASE_SERVICE_ROLE_KEY
```
