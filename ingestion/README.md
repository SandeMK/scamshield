# Threat Intelligence DB + Feed Ingestion (Deliverables 3.2.3 & 3.2.4)

## Components
- `schema.sql` — Supabase/PostgreSQL schema: `indicators` (hashed, with
  first_seen / last_seen / hit_count / reputation metadata), `reports`,
  and the `ingest_indicators` upsert RPC. RLS enabled: only the service
  key can access the tables.
- `ingest.py` — fetches URLhaus + OpenPhish, normalizes, SHA-256 hashes
  (no raw URLs stored beyond hashes; privacy by design), deduplicates,
  and batch-upserts via RPC. One feed failing does not block the other.
- `.github/workflows/ingest.yml` — automated daily run at 04:00 UTC
  (06:00 SAST) + manual trigger. Credentials come from repo secrets.

## One-time setup
1. Supabase -> SQL Editor -> paste `schema.sql` -> Run.
2. GitHub repo -> Settings -> Secrets and variables -> Actions ->
   add `SUPABASE_URL` and `SUPABASE_SERVICE_KEY`.
3. Actions tab -> "Threat Feed Ingestion" -> Run workflow (first import).

## Design notes
- Each malicious URL yields two indicators: the exact URL (reputation 90/85)
  and its domain (reputation -20) — domains are weaker evidence but catch
  new paths on known-bad hosts.
- Re-observing an indicator bumps `hit_count`, refreshes `last_seen`, and
  keeps the highest reputation — the metadata required by §3.2.3.
- The scoring API checks URL hash first, then domain hash, and adds an
  `INTEL_MATCH` reason code (+25 score) on a hit. Lookups have a 1.5 s
  timeout and fail open so scoring never breaks if the DB is down.
