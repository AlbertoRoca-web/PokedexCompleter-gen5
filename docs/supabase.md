# Supabase Setup

Supabase is optional right now. The current app can inspect saves and generate reports without it.

Use Supabase later for:

- cloud report history;
- user accounts;
- task sync;
- emulator session logs;
- labeled screenshot storage;
- supervised learning feedback.

## GitHub secrets

Add these in GitHub:

```text
Repo -> Settings -> Secrets and variables -> Actions -> New repository secret
```

Recommended names:

```text
SUPABASE_URL
SUPABASE_ANON_KEY
SUPABASE_PUBLISHABLE_KEY
SUPABASE_SERVICE_ROLE_KEY
```

The service-role key is powerful. Use it only in trusted server-side code or GitHub Actions jobs that require privileged access.

## Local environment

Create `.env` locally. Do not commit it.

```env
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_PUBLISHABLE_KEY=
SUPABASE_SERVICE_ROLE_KEY=
```

The Python helper also accepts Supabase's Next.js-style public names:

```env
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=
```

## Python backend usage

Install backend extras:

```powershell
uv sync --extra backend
```

Create a normal publishable-key client:

```python
from pokedex_completer_gen5.backend.supabase_client import create_supabase_client

supabase = create_supabase_client()
```

Create a service-role client only in trusted server-side contexts:

```python
supabase = create_supabase_client(use_service_role=True)
```

## About Supabase's Next.js snippet

Supabase's dashboard may show instructions like:

```powershell
npm install @supabase/supabase-js @supabase/ssr
```

and files such as:

```text
.env.local
page.tsx
utils/supabase/server.ts
utils/supabase/client.ts
utils/supabase/middleware.ts
```

Those are for a Next.js frontend. This repo is currently Python/FastAPI-first, so those files were not added.

If/when a Next.js dashboard is created under a `web/` or `dashboard/` folder, add those packages/files inside that frontend package, not at the Python repo root.

## MCP note

Supabase may offer "agent skills" or MCP-related helpers for AI coding tools. Those are useful for development workflows, but they are separate from this app's own MCP server skeleton.

Current app MCP skeleton lives at:

```text
src/pokedex_completer_gen5/server/mcp.py
```
