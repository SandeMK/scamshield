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
