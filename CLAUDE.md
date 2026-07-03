# ScamShield — Project Context

ISJ107V Integrated Software Project (TUT). Smishing (SMS phishing) detection
for South Africa: Flutter app + FastAPI hybrid (rules + ML) scoring API +
Supabase threat-intel DB + public feed ingestion. Graded against
`Assignment 2` (see the submitted doc) — its section numbers (§12, §13.3,
FR-xx, NFR-xx, ET-xx) are the authoritative spec for contracts and naming.

## Layout
- `ml/` — features.py (rules + engineered features, source of explanation
  codes), train.py (auto-downloads dataset; 5-fold CV model selection:
  LogReg won, F1 0.942 held-out), score.py (hybrid fusion: 60% ML + 40%
  rules, critical override >= 90; labels SAFE..CRITICAL)
- `api/` — FastAPI on /api/v1 (score/sms, score/url, report,
  analytics/summary, health, intel/ingest). X-API-Key auth (env API_KEY,
  dev default "demo-key"; admin: ADMIN_KEY). Supabase intel client activates
  when SUPABASE_URL + SUPABASE_SERVICE_KEY env vars are set, else stub.
- `ingestion/` — schema.sql (run in Supabase SQL editor; already applied),
  ingest.py (URLhaus + OpenPhish -> hashed indicators). Runs daily via
  GitHub Actions (secrets already configured in repo settings).
- `mobile-app/` — Flutter source in lib/ + platform/MainActivity.kt
  (EventChannel 'scamshield/sms'). NOT a runnable project by itself:
  `./setup.sh` runs `flutter create` into `mobile-app/app/` (gitignored
  build dirs) and copies the source in. Requires Flutter >= 3.22.
- `fintech-client/` — third-party interoperability demo (client.py).
- `api/postman_collection.json` — contract tests (§14.4).

## Commands
- API: `cd api && uvicorn main:app --host 0.0.0.0 --port 8000`
- Tests: `python -m pytest tests/` inside ml/, api/, ingestion/ (17 total)
- Retrain: `cd ml && python train.py` (do this if sklearn version changes;
  model.joblib is committed and version-stamped, ET-05)
- App: `cd mobile-app && ./setup.sh && cd app && flutter run`
- Fintech demo: `python fintech-client/client.py --base-url <url>`

## Conventions & decisions (do not silently change)
- Response contract per Assignment 2 §12: risk_score, classification,
  explanation_codes [{code, detail}] (always >= 3), ml_confidence,
  rule_sub_score, model_version.
- Indicators are SHA-256 hashed (normalize: strip + lowercase) — identical
  hashing in api/main.py and ingestion/ingest.py; there is a cross-module
  test enforcing this.
- DB is Supabase (PostgreSQL), a documented deviation from the Firestore
  in Assignment 2 (rationale in root README). Exact URL intel match floors
  score at 90 (CRITICAL); domain match +15.
- Never commit secrets. Supabase creds live in GitHub Actions secrets and
  local env vars only. App is demo-only: sideloaded, no Play Store.

## Current state / next steps
1. User is getting the Flutter app running locally (physical Samsung
   device — API base URL must be the Mac's LAN IP, not 10.0.2.2).
2. TODO: deploy API to Render free tier (Dockerfile exists at
   api/Dockerfile; add render.yaml, keep-alive ping for demo day).
3. TODO: Flutter widget tests (§14.2) and integration test (§14.3).
4. TODO: measure + record §14.6 metrics (100-request latency batch,
   30 s propagation test) for the final report.
5. Known model quirk for the report: legitimate bank/OTP notifications can
   score MEDIUM_RISK (shared vocabulary with phishing) — discussed as a
   finding, mitigated by tiered actions + false-positive reporting.
