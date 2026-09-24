-- ScamShield Shared Threat Intelligence Database (Deliverable 3.2.3)
-- Run this once in Supabase: SQL Editor -> New query -> paste -> Run.

create table if not exists indicators (
    id              bigint generated always as identity primary key,
    indicator_hash  text not null,            -- sha256 of normalized value (privacy)
    indicator_type  text not null check (indicator_type in ('url', 'domain', 'template')),
    source          text not null,            -- 'urlhaus' | 'openphish' | 'user_report'
    threat_tag      text,                     -- e.g. 'phishing', 'malware_download'
    reputation      integer not null default 50 check (reputation between 0 and 100),
    hit_count       integer not null default 1,
    first_seen      timestamptz not null default now(),
    last_seen       timestamptz not null default now()
);

-- One row per unique indicator+type; sources merge into the same row.
create unique index if not exists indicators_hash_type_uq
    on indicators (indicator_hash, indicator_type);

create index if not exists indicators_last_seen_idx on indicators (last_seen desc);

-- User reports (scam / false positive) from the mobile app (§3.2.1)
create table if not exists reports (
    id              bigint generated always as identity primary key,
    report_type     text not null check (report_type in ('scam', 'false_positive')),
    text_hash       text,
    url_hash        text,
    created_at      timestamptz not null default now()
);

-- Insert-or-update an indicator: refresh last_seen, bump hit_count,
-- keep the highest reputation seen. Called via PostgREST RPC in batches.
create or replace function ingest_indicators(batch jsonb)
returns integer
language plpgsql
security definer
as $$
declare
    item jsonb;
    n integer := 0;
begin
    for item in select * from jsonb_array_elements(batch)
    loop
        insert into indicators (indicator_hash, indicator_type, source, threat_tag, reputation)
        values (
            item->>'indicator_hash',
            item->>'indicator_type',
            item->>'source',
            item->>'threat_tag',
            coalesce((item->>'reputation')::integer, 50)
        )
        on conflict (indicator_hash, indicator_type) do update
            set last_seen  = now(),
                hit_count  = indicators.hit_count + 1,
                reputation = greatest(indicators.reputation, excluded.reputation);
        n := n + 1;
    end loop;
    return n;
end;
$$;

-- Lock the tables down: only the service key (bypasses RLS) may touch them.
alter table indicators enable row level security;
alter table reports    enable row level security;

-- ---------------------------------------------------------------------------
-- UC-13 Manage Profile & Notifications (FR-14/15/16) — added post-submission,
-- nullable-safe migration on the live tables. device_id is a hub, not a
-- chain: client-generated, anonymous, exists whether or not a profile is
-- ever created. Report -> UserProfile, not the reverse, so a device's scan
-- and report history survives deleting its profile.
-- ---------------------------------------------------------------------------

create extension if not exists pgcrypto;

alter table reports add column if not exists device_id text;
create index if not exists reports_device_id_idx on reports (device_id);

create table if not exists user_profiles (
    user_id             uuid primary key default gen_random_uuid(),
    device_id           text not null unique,
    display_name        text,
    email               text unique,
    notification_prefs  jsonb not null default '{
        "alert_threshold": "MEDIUM_RISK",
        "retroactive_updates": true,
        "report_outcomes": true,
        "digest_frequency": "off"
    }'::jsonb,
    total_scans         integer not null default 0,
    total_reports       integer not null default 0,
    created_at          timestamptz not null default now(),
    last_active         timestamptz not null default now()
);

create index if not exists user_profiles_device_id_idx on user_profiles (device_id);
create index if not exists user_profiles_email_idx on user_profiles (email);

alter table user_profiles enable row level security;

-- Atomic counter bump, called by POST /api/v1/report when device_id is set.
-- A no-op (not an error) if the device has no profile yet.
create or replace function increment_profile_reports(p_device_id text)
returns void
language sql
security definer
as $$
    update user_profiles set total_reports = total_reports + 1, last_active = now()
    where device_id = p_device_id;
$$;
