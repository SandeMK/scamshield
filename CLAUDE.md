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
- `mobile-app/` — Flutter project root. android/ scaffolding fully committed
  (no setup.sh needed). Kotlin: ScamShieldApp.kt (FlutterEngineCache),
  SmsProtectionService.kt (FGS + EventChannel + notify MethodChannel),
  BootReceiver.kt, MainActivity.kt (cached engine + battery prompt).
  Dart: lib/screens/ (home, simulator, dashboard, settings, permission),
  lib/services/ (api_client, scan_store, sms_channel, local_rules).
  Default API URL: https://scamshield-api-4ywt.onrender.com. Requires Flutter >= 3.22.
- `fintech-client/` — third-party interoperability demo (client.py).
- `api/postman_collection.json` — contract tests (§14.4).

## Commands
- API: `cd api && uvicorn main:app --host 0.0.0.0 --port 8000`
- Tests: `python -m pytest tests/` inside ml/, api/, ingestion/ (17 total)
- Retrain: `cd ml && python train.py` (do this if sklearn version changes;
  model.joblib is committed and version-stamped, ET-05)
- App: `cd mobile-app && ./setup.sh && flutter run`
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
App fully built and deployed. Assignment 2 submitted 30 June; demo later.

### DONE
- App runs on physical Samsung S938B (Android 16), sideloaded.
- Foreground service (SmsProtectionService): persistent notification
  "ScamShield is protecting you", SMS EventChannel on Service context
  survives swipe-away, BootReceiver, POST_NOTIFICATIONS permission,
  one-time Samsung battery exemption prompt.
- UI polish: launcher icon (adaptive, #1B5E20), splash screen, first-launch
  permission explainer, animated risk gauge (arc), empty states, filter chips
  (All/Suspicious+/Reported), entrance animations, light mode default.
- Tests: 35 widget tests passing (test/widget_test.dart §14.2);
  integration test written (integration_test/app_test.dart §14.3).
  Run integration test: flutter test integration_test/app_test.dart -d <device>
- API deployed to Render free tier: https://scamshield-api-4ywt.onrender.com
  Keep-alive workflow (.github/workflows/keepalive.yml) pings every 10 min;
  set repo variable API_BASE_URL=https://scamshield-api-4ywt.onrender.com
  in GitHub Settings → Secrets and variables → Actions → Variables.
  render.yaml has port: 8080 fix committed.

### TODO (user)
1. Confirm Render port fix deployed: curl .../api/v1/health returns JSON.
2. Set API_BASE_URL repo variable on GitHub for keep-alive workflow.
3. Run perf/latency_test.py + perf/propagation_test.py against Render URL;
   record numbers for report §14.6.
4. Take screenshots of 4 tabs + CRITICAL detail sheet → docs/screenshots/
   referenced from mobile-app/README.md.

### Report notes
- Legitimate bank/OTP messages can score MEDIUM_RISK (shared vocabulary) —
  document as finding, mitigated by tiered actions + false-positive reporting.
- Foreground-service pilot vs manifest-receiver production approach is a good
  trade-off discussion point.
- Future work: onboarding carousel; isiZulu localisation; manifest-receiver
  architecture for true background SMS without FGS.