# Supabase Persistence

The app can store sanitized Living Dex report metadata in Supabase.

It does not upload save files or ROMs.

## Schema

Initial migration:

```text
supabase/migrations/0001_initial.sql
```

Tables:

```text
dex_reports
planner_tasks
emulator_sessions
agent_events
training_labels
```

## Apply migration

Use the Supabase SQL editor or Supabase CLI.

### Option A: SQL editor

1. Open Supabase project dashboard.
2. Go to SQL Editor.
3. Paste contents of:

```text
supabase/migrations/0001_initial.sql
```

4. Run it.

### Option B: Supabase CLI later

We can wire this later with:

```powershell
supabase link --project-ref your-project-ref
supabase db push
```

Do not commit Supabase access tokens or database passwords.

## Sync a report

Install backend dependency:

```powershell
uv sync --extra backend
```

Make sure local `.env` has:

```env
SUPABASE_URL=
SUPABASE_SECRET_KEY=
```

or:

```env
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
```

Then run:

```powershell
uv run rld sync-report "D:\path\to\POKEMON W.sav" --game white
```

Stored metadata includes:

```text
game_profile
regional_dex_key
planner_supported
selected_copy
unique_species_owned
missing_species_count
save_sha256
sanitized report_json
```

The save path inside `report_json` is reduced to the file name and marked as redacted.

## Privacy rule

Never upload full save blobs by default. If future features need cloud save backups, that must be a separate explicit opt-in feature with encryption and giant warning signs.
