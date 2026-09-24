# ScamShield — Build Plan for Claude Code
*Rewritten [current session] after inspecting the live repo — supersedes the previous version of this file, which assumed nothing had been built. That assumption was wrong: most of the system is built, deployed, and running.*

**Purpose of this document:** hand off from spec-writing (done, in claude.ai) to implementation (Claude Code, on your machine, against `github.com/SandeMK/scamshield`). Status, not instructions — decide sequencing yourself, verify every claim below against the actual repo before trusting it.

---

## 1. The Goal

Same as before: make the running system match `ScamShield_ISJ107V_Assignment2.docx` exactly — every FR/NFR/ET id traceable to running code and a test. What's changed is how much of that is already true.

## 2. Where We Actually Are (verified against github.com/SandeMK/scamshield just now)

**Built, deployed, and working:**
- `ml/` — TF-IDF + Logistic Regression, F1 0.942 held-out (beats the 0.85 target in ET-01), trained on the 5,572-message UCI SMS Spam Collection.
- `api/` — FastAPI on `/api/v1`, all six endpoints from the document's Section 5.1 table, deployed live at `https://scamshield-api-4ywt.onrender.com`. X-API-Key auth working.
- `ingestion/` — URLhaus + OpenPhish, daily via GitHub Actions, schema already applied to a live Supabase project.
- `mobile-app/` — Flutter app, **running on a physical Samsung S938B, sideloaded**. Foreground service, EventChannel/MethodChannel bridge, boot receiver, battery-exemption prompt, 35 passing widget tests, 1 integration test.
- `fintech-client/` — done.
- **FR-10 (share-sheet) — just pushed, and done properly**: `ACTION_SEND`/`ACTION_PROCESS_TEXT` intent filters, a `scamshield/share` MethodChannel handling both cold-start (`getInitialText`) and warm-start (`onNewIntent`) cases correctly, tagged `'shared'` through the same `ScanStore.process()` path as everything else. No backend changes needed, which checks out — FR-10 was always meant to reuse the existing pipeline.
- Dashboard (now **FR-13** in the current document — see §3 below on why the numbering moved) — done, shipped as part of `mobile-app/`.

**Built since the last version of this plan:**
- **FR-09, Guardian Alert — done, mobile-only, no backend changes.** `SEND_SMS`
  permission requested only when the user opts in from Settings (trusted-
  contact field + plain-language dialog before the OS prompt), never at
  first launch. `scamshield/guardian` MethodChannel on `MainActivity` handles
  the permission check/request (needs an Activity); sending is a new
  `guardianAlert` case on the existing Service-owned `scamshield/notify`
  channel (`SmsManager.getDefault().sendMultipartTextMessage`), so it still
  fires if the app has been swiped away. `ScanStore._maybeGuardianAlert`
  gates on `scan.result?.classification == 'CRITICAL'` — the field set only
  from the cloud response — so the NFR-02 offline path and the provisional
  local warning never trigger it. Trusted contact number is
  `shared_preferences` key `guardianContact`, local-only, never sent to
  Supabase.
- **UC-13 Manage Profile & Notifications (FR-14/15/16) — done, mobile +
  backend.** `device_id` generated client-side at first use
  (`lib/services/device_id.dart`), sent with every report regardless of
  profile. Backend gained `ProfileStore`/`SupabaseProfileStore` (mirrors
  `ThreatIntelClient`'s stub/live split) and five endpoints: POST
  `/api/v1/profile`, GET `/api/v1/profile/{device_id}`, PATCH
  `/api/v1/profile/notifications`, POST `/api/v1/profile/recovery/request`,
  POST `/api/v1/profile/recovery/verify`. FR-16 recovery rides Supabase
  Auth's own email-OTP flow (`/auth/v1/otp` + `/auth/v1/verify`) instead of
  a hand-rolled code table or a new SMTP dependency — still a genuine
  "6-digit emailed code" per §4, just issued by infrastructure the project
  already has. Settings screen gained Profile / Notification Preferences /
  Recover-a-profile sections. Schema migration appended (idempotently) to
  `ingestion/schema.sql`, **not yet re-applied to the live Supabase DB** —
  see the new item in §6.

**Not built — nothing left from the graded scope.** What remains is two manual, code-external steps (§6) and the repo's pre-existing TODOs (§6.6, unrelated to FR-09/14/15/16).

## 3. Something to Reconcile Before Building Further — Documentation Has Drifted From the Spec

The repo's `CLAUDE.md` and root `README.md` were clearly written against an **earlier version** of the Assignment 2 document than the one that now exists. Two concrete drifts:

- **The "Firestore deviation" note is now stale.** `CLAUDE.md` states: *"DB is Supabase (PostgreSQL), a documented deviation from the Firestore in Assignment 2 (rationale in root README)."* The current document never mentions Firestore at all — Supabase/PostgreSQL is specified directly as the primary design, not a deviation from anything. This isn't a code problem, it's a stale sentence in two files (`README.md`, `CLAUDE.md`) that should be corrected so a marker reading both the code and the doc doesn't get confused by a "deviation" that no longer exists on the doc side.
- **FR-09 has changed meaning.** In the repo's mental model, FR-09 doesn't exist yet as anything; in the current document, FR-09 is Guardian Alert (the analytics dashboard — the *original* FR-09 — was deliberately moved to FR-13 to make room for it). `CLAUDE.md`'s "Layout" and "Conventions" sections should be updated to reflect the current FR-01…FR-16 numbering once Guardian Alert and the profile features exist, so the next person reading `CLAUDE.md` isn't working from outdated ids.

Do this reconciliation as part of implementing §2's remaining work, not as a separate pass — update `CLAUDE.md`/`README.md` claims in the same commits that make them true.

## 4. Key Decisions Already Made (unchanged from before — still carry these over)

- **Guardian Alert is fully automatic** (`SmsManager.sendTextMessage`), not tap-to-send — deliberately rejected the tap-to-send version because the feature protects the person least likely to act on their own mid-scam.
- **The guardian contact number is local-only** — never sent to or stored in Supabase.
- **`device_id` is a hub, not a chain** — client-generated, anonymous, exists whether or not a profile is ever created. `reports` and `user_profiles` both carry it; the relationship points `Report → UserProfile`, not the reverse, so a device's history survives deleting its profile.
- **Profile creation is opt-in from Settings, never a first-launch gate.**
- **`notification_prefs` lives on the profile, not the device** — deliberate, not a technical requirement.
- **Recovery is a 6-digit emailed code**, restoring `display_name`/`notification_prefs`/counters only — not the old device's detailed history. Accepted limitation, not a bug.
- **No "fintech client" FR exists** — the Fintech Partner System is just an actor consuming FR-02 directly.

## 5. What Was Tried and Rejected (unchanged — still valid, don't rediscover)

- Firestore/document-store schema was briefly assumed mid-conversation based on a stale memory of a different earlier version of this project, then corrected. The real, current, and now-*implemented* stack is relational (Supabase/Postgres) — see §3, this is exactly the drift now sitting in the repo's docs.
- Linked-device history preservation on recovery — considered, explicitly rejected in favour of the simpler single-device model.

## 6. Remaining Work — Concrete, in the Order I'd Do It

1. ~~Guardian Alert (FR-09)~~ — **done**, see §2.
2. ~~`user_profiles` + `device_id` migration, FR-14, FR-15, FR-16~~ — **done**, see §2. Two manual steps are still needed before the deployed system actually has this behavior (code alone can't do either):
   - **Re-run `ingestion/schema.sql` in the Supabase SQL editor.** Every new statement is idempotent (`if not exists` / `create or replace`), so re-running the whole file is safe. Until this runs, the live DB has no `device_id` column, no `user_profiles` table, and no `increment_profile_reports` function — the new endpoints will 500 or fail silently against the deployed Supabase project.
   - **Supabase dashboard → Authentication → Email Templates → Magic Link: add `{{ .Token }}` to the body.** Without it, the FR-16 recovery email is a magic-link button with no visible 6-digit code, and there's nothing for the user to type into the verify step. This is the one piece of the Supabase-Auth-OTP approach (§4) that can't be done from code.
3. **Documentation reconciliation (§3)** — done in the same commits.
4. **The repo's own outstanding TODOs** (from `CLAUDE.md`, unrelated to FR-09/14/15/16, still open as of the last push):
   - Confirm the Render port fix actually deployed (`curl .../api/v1/health`).
   - Set the `API_BASE_URL` repo variable so the keep-alive workflow can run.
   - Run `perf/latency_test.py` and `perf/propagation_test.py` against the live Render URL and record the numbers for the report.
   - Screenshot the four tabs + the CRITICAL detail sheet into `docs/screenshots/`.

## 7. Suggested Skills / Tools for Claude Code

- Standard Flutter/Dart, Python, and `supabase-py` or raw SQL tooling — nothing special needed.
- The repo already has a Postman collection (`api/postman_collection.json`) and 17 passing tests across `ml/`, `api/`, `ingestion/` — extend these rather than starting new test suites for FR-09/14/15/16.

## 8. Context Manifest

| Item | What it is | Why it matters |
|---|---|---|
| `ScamShield_ISJ107V_Assignment2.docx` | The graded specification — source of truth | Every FR/NFR/ET id, DB schema, API table, pseudocode |
| `https://github.com/SandeMK/scamshield` | The live repo | Everything in §2 was verified here just now — re-verify before trusting further, things move fast |
| `github.com/SandeMK/scamshield/blob/main/CLAUDE.md` | The repo's own living memory | Detailed, current for everything *except* FR-09/14/15/16 and the Firestore note (§3) |
| `diagrams/Figure1-4_*.png` + `.puml` | The four UML diagrams | Class names/attributes and the two conditional branches (local warning, guardian alert) off UC-01 must match whatever gets built |
| `https://scamshield-api-4ywt.onrender.com` | Live deployed API | `/api/v1/health` for a liveness check; Swagger at `/docs` |

## 9. Quick-Start Prompt for the Next Session

> All graded FR/NFR/ET work is implemented (FR-01..FR-16). What's left is two manual, code-external steps (§6.2) — re-run `ingestion/schema.sql` against the live Supabase project, and add `{{ .Token }}` to its Magic Link email template — plus the repo's pre-existing TODOs (§6.4: confirm Render deploy, record perf numbers, take screenshots). Assignment 2 is due 19 September 2026 and has NOT been submitted yet (an earlier CLAUDE.md note claiming "submitted 30 June" was stale and has been corrected). Verify this plan's done/not-done claims against the actual repo before trusting them.
