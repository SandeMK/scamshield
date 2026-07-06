opme# ScamShield — Project Context

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
- `mobile-app/` — Flutter project root. lib/ + pubspec.yaml + platform/
  MainActivity.kt (EventChannel 'scamshield/sms') are committed. `./setup.sh`
  runs `flutter create .` in-place to generate android/ scaffolding, patches
  permissions + MainActivity, then `flutter pub get`. Requires Flutter >= 3.22.
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
App builds and runs on the user's physical Samsung (S938B, Android 16).
Assignment 2 was submitted 30 June; demo is later — no immediate deadline.

1. TODO (mobile-app, Claude Code): persistent background SMS capture via
   FOREGROUND SERVICE. Agreed spec:
   - Kotlin foreground Service with persistent notification
     ("ScamShield is protecting you"); started on app launch.
   - Cache the Flutter engine via FlutterEngineCache in an Application
     subclass so the existing EventChannel pipeline survives the activity
     being swiped away. Do NOT rebuild the pipeline natively and do NOT
     use headless/manifest-receiver architecture (documented as future
     work instead).
   - Manifest: FOREGROUND_SERVICE permission + foregroundServiceType
     "specialUse" (sideload-only, no Play review concern).
   - Optional: BOOT_COMPLETED receiver to restart after reboot.
   - One-time prompt guiding the user to Samsung battery exemption
     (Settings -> Battery -> app -> Unrestricted); One UI kills FGS
     apps otherwise.
   - High-risk results while backgrounded should post a notification.
2. TODO (mobile-app, Claude Code): UI polish pass. Priority order:
   a. Wire branding per mobile-app/branding/README.md: launcher icon via
      flutter_launcher_icons + android:label="ScamShield" (patch label in
      setup.sh so regeneration keeps it).
   b. Splash screen: flutter_native_splash, background #1B5E20, shield
      from branding/ (use icon-foreground.png).
   c. First-launch permission explainer screen BEFORE the Android SMS
      permission dialog: brief privacy-by-design copy (messages scanned,
      only SHA-256 hashes ever stored server-side), then request.
   d. Animated risk gauge in the scan detail sheet: 0-100 arc sweeping to
      the score, coloured by classification band (util.dart colours).
   e. Empty-state visuals for Scans and Dashboard tabs (shield icon +
      friendly copy) replacing plain text.
   f. Dark mode: darkTheme with the same seed colour (#1B5E20).
   g. Filter chips on Scans tab: All / Suspicious+ (MEDIUM_RISK and up) /
      Reported.
   h. Subtle entrance animation for new scan cards.
   Later / future work: onboarding carousel; isiZulu localization
   (mention in report's Future Work if skipped).
3. TODO (mobile-app, Claude Code): widget tests (§14.2), integration
   test (§14.3) — good targets: gauge/card colour per classification,
   explanation list rendering, report button state change.
4. TODO (user + chat): deploy API to Render free tier — render.yaml is
   ready; then set repo variable API_BASE_URL for the keep-alive workflow.
5. TODO: run perf/latency_test.py and perf/propagation_test.py against
   the deployed URL; record numbers for the report (§14.6).
6. TODO (user): docs/screenshots/ of the four tabs + a CRITICAL detail
   sheet, referenced from mobile-app/README.md.
7. Report notes: (a) legitimate bank/OTP messages can score MEDIUM_RISK
   (shared vocabulary) — finding, mitigated by tiered actions +
   false-positive reporting; (b) foreground-service pilot approach vs
   manifest-receiver production approach is a good trade-off discussion.