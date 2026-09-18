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

**Not built at all — this is the real remaining-work list, not what the last version of this plan guessed:**
- **FR-09, Guardian Alert.** No mention anywhere in the repo. This is the one that matters most: it's in the *required ten* in the current document, not an optional extra. Needs: `SEND_SMS` permission flow, a Settings field for the trusted contact number (local storage only — never sent to Supabase), and the `SmsManager.sendTextMessage` call gated on classification == CRITICAL. Nothing here touches the backend.
- **FR-14/15/16 — profile creation, notification preferences, email recovery.** No `user_profiles` table, no `device_id` column on `reports`, no Settings UI for any of it, no recovery-code endpoint. This is real work on both sides: a Supabase migration plus new API endpoints plus new Settings screens.

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

1. **Guardian Alert (FR-09)** — highest priority, it's in the graded top ten and doesn't exist yet.
   - Mobile: `SEND_SMS` permission request (with the plain-language justification dialog), Settings field for the trusted contact number (local storage — `shared_preferences` or secure storage, matching the pattern already used for other local-only settings), wire the send into wherever the final CRITICAL classification is handled.
   - No backend or Supabase changes.
   - Test: confirm it fires only on the *returned cloud* classification, not the provisional local one (matches the activity/sequence diagrams — the branch sits after "final colour-coded result," not after the instant local warning).
2. **`user_profiles` + `device_id` migration** — needed before FR-14/15/16 can exist.
   - Add `device_id` column to `reports` (nullable-safe migration on the live table).
   - Create `user_profiles` table exactly as specified in Section 5.1: `user_id`, `device_id`, `display_name` (nullable), `email` (nullable, unique), `notification_prefs` (JSONB), `total_scans`, `total_reports`, `created_at`, `last_active`. Row-level security matching the existing `indicators`/`reports` policy pattern.
3. **FR-14 (profile creation) + FR-15 (notification prefs)** — Settings UI + two new API endpoints (create/update profile, update notification prefs).
4. **FR-16 (recovery)** — lowest priority of the new work by the document's own framing. Emailed 6-digit code, endpoint to request it, endpoint to verify and re-link `device_id`.
5. **Documentation reconciliation (§3)** — fold into the commits above, not a separate pass.
6. **The repo's own outstanding TODOs** (from `CLAUDE.md`, unrelated to this session's new FRs, but still open as of the last push):
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

> Clone `github.com/SandeMK/scamshield` and read `CLAUDE.md` first — it's detailed and mostly current. Then read `ScamShield_ISJ107V_Assignment2.docx`, which is the graded spec and wins over CLAUDE.md wherever they conflict (see §3 of this plan for the two known drifts: the stale Firestore-deviation note, and FR-09 now meaning Guardian Alert rather than nothing). Verify §2's done/not-done claims against the actual code before trusting them — this plan was written from reading the repo's README and CLAUDE.md, not from running the code. Start with Guardian Alert (FR-09) — it's pure mobile-app work, needs no backend changes, and it's the highest-priority gap. Ask before changing any decision listed in §4.
