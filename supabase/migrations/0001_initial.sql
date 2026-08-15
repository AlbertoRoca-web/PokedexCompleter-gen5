-- Initial cloud persistence schema for PokedexCompleter Gen 5.
--
-- This schema stores report metadata and sanitized JSON outputs.
-- It does not store ROMs or save-file blobs.

create extension if not exists pgcrypto;

create table if not exists public.dex_reports (
    id uuid primary key default gen_random_uuid(),
    created_at timestamptz not null default now(),
    game_profile text not null,
    regional_dex_key text,
    planner_supported boolean not null default false,
    selected_copy integer,
    unique_species_owned integer,
    missing_species_count integer,
    save_sha256 text,
    report_json jsonb not null
);

create index if not exists dex_reports_created_at_idx
    on public.dex_reports (created_at desc);

create index if not exists dex_reports_game_profile_idx
    on public.dex_reports (game_profile);

create table if not exists public.planner_tasks (
    id uuid primary key default gen_random_uuid(),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    game_profile text not null,
    status text not null default 'pending',
    priority integer not null default 100,
    task_type text not null,
    species_id integer,
    species_name text,
    payload jsonb not null default '{}'::jsonb
);

create index if not exists planner_tasks_status_priority_idx
    on public.planner_tasks (status, priority, created_at);

create table if not exists public.emulator_sessions (
    id uuid primary key default gen_random_uuid(),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    game_profile text not null,
    emulator text not null default 'BizHawk',
    core text not null default 'melonDS',
    status text not null default 'created',
    metadata jsonb not null default '{}'::jsonb
);

create table if not exists public.agent_events (
    id uuid primary key default gen_random_uuid(),
    created_at timestamptz not null default now(),
    session_id uuid references public.emulator_sessions(id) on delete set null,
    event_type text not null,
    payload jsonb not null default '{}'::jsonb
);

create index if not exists agent_events_session_created_at_idx
    on public.agent_events (session_id, created_at);

create table if not exists public.training_labels (
    id uuid primary key default gen_random_uuid(),
    created_at timestamptz not null default now(),
    session_id uuid references public.emulator_sessions(id) on delete set null,
    label_type text not null,
    label text not null,
    source text not null default 'human',
    payload jsonb not null default '{}'::jsonb
);

create index if not exists training_labels_type_created_at_idx
    on public.training_labels (label_type, created_at desc);
