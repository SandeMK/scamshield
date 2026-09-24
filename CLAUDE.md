# ScamShield — Project Context

ISJ107V Integrated Software Project (TUT). Smishing (SMS phishing) detection
for South Africa: Flutter app + FastAPI hybrid (rules + ML) scoring API +
Supabase threat-intel DB + public feed ingestion. Graded against
`Assignment 2` — due 19 September 2026 (see `plans/ScamShield_Assignment2_SPEC.md`,
the source of truth) — its section numbers (§12, §13.3, FR-xx, NFR-xx, ET-xx)
are the authoritative spec for contracts and naming.

## Layout
- `ml/` — features.py (rules + engineered features, source of explanation
  codes), train.py (auto-downloads dataset; 5-fold CV model selection:
  LogReg won, F1 0.942 held-out), score.py (hybrid fusion: 60% ML + 40%
  rules, critical override >= 90; labels SAFE..CRITICAL)
- `api/` — FastAPI on /api/v1 (score/sms, score/url, report,
  analytics/summary, health, intel/ingest, profile, profile/{device_id},
  profile/notifications, profile/recovery/request, profile/recovery/verify).
  X-API-Key auth (env API_KEY, dev default "demo-key"; admin: ADMIN_KEY).
  Supabase intel client (ThreatIntelClient/SupabaseThreatIntelClient) and
  profile store (ProfileStore/SupabaseProfileStore) both activate when
  SUPABASE_URL + SUPABASE_SERVICE_KEY env vars are set, else stub — same
  pair of env vars, no new secrets needed for FR-14/15/16.
- `ingestion/` — schema.sql (run in Supabase SQL editor; **not yet re-applied
  since the FR-14/15/16 additions** — device_id column on reports,
  user_profiles table, increment_profile_reports RPC — re-running the whole
  file is safe, every statement is idempotent), ingest.py (URLhaus +
  OpenPhish -> hashed indicators). Runs daily via GitHub Actions (secrets
  already configured in repo settings).
- `mobile-app/` — Flutter project root. android/ scaffolding fully committed
  (no setup.sh needed). Kotlin: ScamShieldApp.kt (FlutterEngineCache),
  SmsProtectionService.kt (FGS + EventChannel + notify MethodChannel),
  BootReceiver.kt, MainActivity.kt (cached engine + battery prompt).
  Dart: lib/screens/ (home, simulator, dashboard, settings, permission),
  lib/services/ (api_client, scan_store, sms_channel, share_channel,
  guardian_channel, device_id, local_rules).
  Default API URL: https://scamshield-api-4ywt.onrender.com. Requires Flutter >= 3.22.
- `fintech-client/` — third-party interoperability demo (client.py).
- `api/postman_collection.json` — contract tests (§14.4).

## Commands
- API: `cd api && uvicorn main:app --host 0.0.0.0 --port 8000`
- Tests: `python -m pytest tests/` inside ml/, api/, ingestion/ (17 total)
- Retrain: `cd ml && python train.py` (do this if sklearn version changes;
  model.joblib is committed and version-stamped, ET-05)
- App: `cd mobile-app && flutter pub get && flutter run`
- Fintech demo: `python fintech-client/client.py --base-url <url>`

## Conventions & decisions (do not silently change)
- Response contract per Assignment 2 §12: risk_score, classification,
  explanation_codes [{code, detail}] (always >= 3), ml_confidence,
  rule_sub_score, model_version.
- Indicators are SHA-256 hashed (normalize: strip + lowercase) — identical
  hashing in api/main.py and ingestion/ingest.py; there is a cross-module
  test enforcing this.
- DB is Supabase (PostgreSQL), specified directly in Assignment 2 §5.1/§3.1
  (not a deviation — an earlier CLAUDE.md/README claim that this was a
  Firestore deviation was stale against the current spec and has been
  corrected). Exact URL intel match floors score at 90 (CRITICAL); domain
  match +15.
- Never commit secrets. Supabase creds live in GitHub Actions secrets and
  local env vars only. App is demo-only: sideloaded, no Play Store.

## Current state / next steps
App fully built and deployed. Assignment 2 due 19 September 2026 — NOT yet
submitted (an earlier version of this note said "submitted 30 June", which
predates the current spec's due date and was stale; corrected here).

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
- Share-to-ScamShield (FR-10): any-channel checking (WhatsApp, email,
  Telegram...) via Android share sheet, user-consented, no interception.
  AndroidManifest ACTION_SEND + ACTION_PROCESS_TEXT intent-filters on
  MainActivity; 'scamshield/share' MethodChannel (cold-start pull via
  onCreate + getInitialText, warm-start push signal via onNewIntent,
  since the activity uses the cached engine and the Dart isolate is
  Application-scoped); ScanStore.process(text, 'SHARED', 'shared'), jump
  to Scans tab, 'shared' tag on the card (like 'simulated'). No backend
  changes needed. Repo cleanup (gitignore/.idea, setup.sh removal,
  defaultApiKey, stale comment, mobile-app/README.md) all done.
- Guardian Alert (FR-09) — done, mobile-only, no backend changes.
  SEND_SMS permission requested only when the user opts in from Settings
  (trusted-contact field), never at first launch alongside RECEIVE_SMS;
  a plain-language dialog precedes the OS permission prompt.
  `scamshield/guardian` MethodChannel (MainActivity) handles
  hasSendSmsPermission/requestSendSmsPermission — needs an Activity
  context, so it can't live on the foreground service. Sending is a new
  "guardianAlert" case on the existing Service-owned 'scamshield/notify'
  channel (SmsManager.getDefault().sendMultipartTextMessage), so it keeps
  firing even if the app has been swiped away. ScanStore._maybeGuardianAlert
  gates strictly on scan.result?.classification == 'CRITICAL' (the returned
  cloud result, set only inside the try-block after api.scoreSms succeeds)
  — never on localScore — so the NFR-02 offline path and the provisional
  local warning can never trigger it, matching the activity/sequence
  diagrams. Trusted contact number: shared_preferences key
  'guardianContact', local-only, never sent to Supabase (per §4 decision).
- UC-13 Manage Profile & Notifications (FR-14/15/16) — done, mobile +
  backend. `device_id`: 32-hex anonymous id generated client-side at first
  use (lib/services/device_id.dart, no new pub dependency), persisted in
  shared_preferences, sent with every /api/v1/report call regardless of
  whether a profile exists. Backend: `ProfileStore`/`SupabaseProfileStore`
  in api/main.py mirror the ThreatIntelClient stub/live split exactly.
  FR-14: POST /api/v1/profile upserts on device_id (PostgREST
  `on_conflict=device_id` + `resolution=merge-duplicates`), seeding
  total_scans/total_reports from the client's local counts only on first
  creation (spec: "immediately inherits the totals already associated with
  that device"). FR-15: PATCH /api/v1/profile/notifications, 404 if no
  profile exists for that device_id. FR-16 recovery deliberately has **no**
  hand-rolled OTP table — it rides Supabase Auth's own email-OTP flow
  (POST {SUPABASE_URL}/auth/v1/otp to send, /auth/v1/verify to check),
  reusing the project's existing Supabase instance instead of adding a new
  SMTP/email-provider dependency this close to the deadline; on verify
  success the backend PATCHes user_profiles.device_id to re-link. The stub
  ProfileStore (no Supabase configured) implements its own in-memory OTP
  for local dev/tests only — never wired to a real inbox.
  Settings screen gained Profile / Notification preferences / Recover-a-
  profile sections (mutually exclusive: recovery only shows when no
  profile exists yet). 9 new api/tests/test_api.py cases (17 total).
  Postman collection: 5 new requests (Create/update profile, Get profile,
  Update notification preferences, Request/Verify recovery code).

### TODO (user)
1. Confirm Render port fix deployed: curl .../api/v1/health returns JSON.
2. Set API_BASE_URL repo variable on GitHub for keep-alive workflow.
3. Run perf/latency_test.py + perf/propagation_test.py against Render URL;
   record numbers for report §14.6.
4. Take screenshots of 4 tabs + CRITICAL detail sheet → docs/screenshots/
   referenced from mobile-app/README.md.
5. **Re-run `ingestion/schema.sql` in the Supabase SQL editor** — the
   FR-14/15/16 additions (device_id column, user_profiles table,
   increment_profile_reports function) are not live on the deployed DB
   until this runs. Safe to re-run the whole file (idempotent).
6. **Supabase dashboard → Authentication → Email Templates → Magic Link**:
   add `{{ .Token }}` to the template body. Without this, FR-16's recovery
   email is a magic-link button with no visible 6-digit code, and the
   verify step (which expects a token) has nothing for the user to type.
   This is a one-time manual dashboard change — cannot be done from code.
7. Supabase free-tier's built-in email sending is low-volume (intended for
   testing, not production traffic) — fine for the pilot/demo, worth a
   one-line caveat in the report if FR-16 is demoed live.

### Report notes — channel scope (WhatsApp/email question)
Proposal + Assignment 2 are deliberately SMS-only. Defense: Android
exposes SMS via an official broadcast API; WhatsApp is E2E-encrypted with
no third-party access API (only fragile, ToS-violating accessibility or
notification scraping, contradicting privacy-by-design); email phishing
is a separately mature problem. SA impersonation scams concentrate on SMS
because it lacks platform filtering. Future work: the scoring API is
channel-agnostic (text + URLs), so Share-to-ScamShield extends coverage
to any app with user consent — implemented/being implemented above.

### Report notes
- Legitimate bank/OTP messages can score MEDIUM_RISK (shared vocabulary) —
  document as finding, mitigated by tiered actions + false-positive reporting.
- Foreground-service pilot vs manifest-receiver production approach is a good
  trade-off discussion point.
- Future work: onboarding carousel; isiZulu localisation; manifest-receiver
  architecture for true background SMS without FGS.