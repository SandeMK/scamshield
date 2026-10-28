# A4 Build Brief — ScamShield prototype fixes

For: Claude Code, working in `SandeMK/scamshield` on the student's laptop.
Parent document: `BRIEF.md` (confirmed 28 Oct 2026). If this brief and the code disagree, **stop and ask** rather than guess.
Goal: close two weaknesses found in Assignment 3 before the Assignment 4 live demo, **without retraining the model**, then re-measure everything the report quotes.

Work on a branch: `git checkout -b a4/prototype-fixes`. Open a PR into `main` when all checks below pass.

---

## 0. Pre-flight: establish what is actually deployed (do this first, change nothing)

The A3 report states: the deployed classifier is Random Forest `v1.0.0`, trained under scikit-learn 1.9.0, held-out F1 0.934. The repo's last commit is 24 Sep, and `ml/requirements.txt` says `scikit-learn>=1.4`, so these claims may not all be true of the code on `main`.

1. Run `python -c "import joblib; b=joblib.load('ml/model.joblib'); print(b.get('model_name'), b.get('model_version'), b.keys())"`.
2. Call `GET /api/v1/health` on the deployed Render API and note the `model_version` it reports.
3. Check for uncommitted local work from A3 (`git status`, `git stash list`, other branches).
4. **Report back** the model name, the model version and the scikit-learn version it loads under. If the repo model is not Random Forest, or if deployed and repo disagree, **stop and tell the student**. The A4 report must describe whatever is really deployed.

## 1. Hard constraint: the model's inputs must not change

`extract_rules()` feeds both the explanation codes and the model (`rule_feature_vector`, `full_feature_vector` → `ScamScorer.score`). `engineered_features()` also uses `URL_PATTERN`. Any change to `URL_PATTERN`, `FEATURE_ORDER` or the existing nine rules changes what the trained model sees and silently invalidates F1 0.934.

Therefore:
- **Freeze the model-input path.** Rename the current regex to `MODEL_URL_PATTERN` (keep its exact text). Use it, and only it, in `engineered_features()` and for the `URL_PRESENT` model feature. Do not add codes to `FEATURE_ORDER`.
- New detection lives in a **separate post-model rule layer**. It adds to `rule_sub_score`, adds explanation codes and supplies `urls` for intelligence lookup. It never adds to the feature vectors.
- **Regression test (required):** compute `full_feature_vector()` for every message in the UCI dataset (the same loader `train.py` uses) before and after the change, and assert they are identical. Then re-run the held-out evaluation in `train.py`'s evaluation mode, or an equivalent eval script that loads `model.joblib` without refitting, and confirm F1 is unchanged. Record the exact number.

## 2. Fix A: scheme-less links are extracted and checked

**Problem (A3):** `"SARS refund of R3,450 approved. Claim now: bit.ly/sars-rf"` returned `"urls": []`. The `.ly` TLD isn't in the pattern, so the link got no intelligence lookup and the message scored 63 (MEDIUM_RISK).

**Change (`ml/features.py`):**
- Add `LINK_PATTERN` for intelligence and explanation purposes. It matches `https?://…`, `www.…`, and bare `host.tld/path` where the TLD is any 2–24 letter label, and it includes common shorteners (bit.ly, t.co, is.gd, rb.gy, cutt.ly, tinyurl.com, ow.ly, shorturl.at, tiny.cc, goo.gl). Avoid false hits on things like `R3.50`, `e.g.`, decimals, times and email addresses (exclude matches preceded by `@`).
- Add `canonical_url(raw) -> str`. It strips trailing punctuation (`.,;:!?)"'`), and if there is no scheme it prefixes `http://`. It does not otherwise rewrite the URL.
- `RuleResult.urls` = canonicalised `LINK_PATTERN` matches, de-duplicated with order preserved.

**Change (`api/main.py`):**
- `SupabaseThreatIntelClient.lookup()`: for a URL with no scheme in the original text, query the URL hash for both `http://` and `https://` variants, then fall back to the domain check. Keep the 1.5 s timeout and the fail-open behaviour. Keep it to at most 3 queries per URL, and look up at most the first 3 URLs per message, to protect NFR-01.
- `/report` already uses `extract_rules(...).urls`, so reported bare links are now stored in canonical form. Leave `hash_indicator()` and `ingestion/ingest.py` hashing exactly as they are; the existing cross-module hash test must still pass.

**Fix A2 (small guard, same PR):** never write a **domain**-level indicator for a URL-shortener domain or for an official brand domain (allowlist in §3). Otherwise one reported `bit.ly/...` scam adds +15 to every bit.ly link for every user, and the demo itself would create this false-positive problem. URL-level indicators for shortened links are still stored. Apply the same exclusion when looking up domains.

**Mobile (`mobile-app/lib/services/local_rules.dart`):** port `LINK_PATTERN` so the provisional on-device card also counts bare links. The local engine is not a model input, so it can change freely.

## 3. Fix B: South African brand impersonation via mismatched links

**Problem (A3):** realistic SA lures are under-scored because the UCI training corpus is older British SMS. Fix this with explainable rules, not retraining.

**Add to the post-model rule layer (`ml/features.py`):**
- `BRANDS`: a dict of brand → keywords and official domains. Cover at least FNB, Absa, Standard Bank, Capitec, Nedbank, TymeBank, SARS (incl. eFiling), SASSA, NSFAS, SA Post Office, The Courier Guy, PostNet, Vodacom, MTN and Telkom. **Verify each official domain** (e.g. `fnb.co.za`, `sars.gov.za`, `sassa.gov.za`) rather than guessing; list any you couldn't verify in the PR description.
- New codes (plain-language details, shown in the app):
  - `BRAND_LOOKALIKE_DOMAIN`, weight 30: a link's host contains a brand keyword but is not that brand's official domain or a subdomain of it (e.g. `fnb-verify.co.za`, `sars-refund.xyz`). Detail: "Link imitates {Brand} but is not {Brand}'s official website".
  - `BRAND_LINK_MISMATCH`, weight 20: the text names a brand, a link is present, and no link points to that brand's official domain (covers shorteners and unrelated hosts). Detail: "Mentions {Brand} but the link leads somewhere else". Only one of the two brand codes fires per message, with LOOKALIKE taking priority.
- Neither code fires when there is **no link**. This keeps genuine OTP and notice SMS such as "Your FNB OTP is 123456" unaffected.
- Codes still respect the existing cap of 6 explanation codes. Place the brand code early in the list so it survives the cap.

**Mobile:** port the two brand checks to `local_rules.dart`, using the same brand list and the same no-link condition.

## 4. Tests to add (keep all existing tests green)

Python (`ml/tests`, `api/tests`):
1. `bit.ly/sars-rf`, `fnb-verify.co.za/login` and `www.sassa-grant.online` are each extracted and canonicalised. `R3.50`, `e.g. this`, `12.30pm` and `name@fnb.co.za` are not.
2. Feature-vector regression (§1) over the full dataset is identical before and after.
3. The SARS sample above and an FNB credential lure (e.g. "FNB: Your account is on hold. Verify your details at fnb-secure-za.com/login within 24 hrs") both reach **HIGH_RISK or above**, and each includes a `BRAND_*` code. If either doesn't, report the actual score; do **not** tune weights beyond the values above without asking.
4. False-positive guard: these legitimate messages score **exactly the same before and after**, with no new codes:
   - "Your FNB OTP is 482913. Never share it with anyone."
   - "SARS: Your eFiling return has been received. Visit https://www.sars.gov.za for status."
   - "Capitec: R250.00 paid to Checkers. Avail bal R1,204.33"
   - "Hey, are we still on for lunch tomorrow at 1?"
5. Intel lookup: in a mocked intel client, a reported `bit.ly/xyz` matches a later scan of `bit.ly/xyz` and of `http://bit.ly/xyz`, and does **not** create a `bit.ly` domain indicator.
6. Existing cross-module hash test (UT-06) still passes.

Flutter (`mobile-app/test`): local rules flag `bit.ly/sars-rf` as a link, and fire the brand code for the FNB lure but not for the FNB OTP message.

## 5. Pin scikit-learn

Pin `scikit-learn==<version that trained ml/model.joblib>` in `ml/requirements.txt`. Per A3 this is 1.9.0, but use what §0 finds. Confirm that the Render build log installs that version and that loading the model raises no `InconsistentVersionWarning`.

## 6. Deploy and re-measure (the report quotes these numbers)

1. Merge, let Render redeploy, and confirm `/health` shows the expected `model_version`.
2. Enable the keep-alive workflow (`API_BASE_URL` repo variable) for the demo period.
3. Run against the **deployed** URL and save the raw output to `docs/RESULTS_A4.md`:
   - `python perf/latency_test.py --base-url <render-url>`: p50, p95, max and % under 2 s.
   - `python perf/propagation_test.py --base-url <render-url>`: propagation time. Run it 3 times and report each value plus the median.
   - the held-out F1, precision, recall and confusion matrix from §1.
   - before/after scores for the SARS and FNB samples, and the four legitimate messages.
   - backend and Flutter test counts (pass/fail).
4. Build the release APK, install it on the Samsung, and re-run device tests ST-01 to ST-07. The student records the actual results.

## 7. Screenshots the student needs (for report and slides)

Capture after the fixes, from the real app:
1. Scans list showing mixed risk bands
2. Detail sheet for the SARS `bit.ly` message, showing the `BRAND_*` and `INTEL_MATCH` codes (after reporting it)
3. Provisional card followed by the final card for the same message
4. "Cloud offline" card (airplane mode)
5. Dashboard
6. WhatsApp → Share → ScamShield result
7. Settings (API config, trusted contact, profile)
8. Guardian Alert SMS on the second phone, if available
9. Terminal: fintech client showing `INTEL_MATCH` after a report
10. Terminal: latency test summary

## 8. Definition of done
- All existing and new tests pass in CI.
- The feature vectors are proven unchanged, and F1 is re-confirmed and recorded.
- The two scam samples reach HIGH_RISK or above, or their actual scores are reported honestly. The four legitimate messages are unchanged.
- scikit-learn is pinned, the deployed `/health` model_version is confirmed, and `docs/RESULTS_A4.md` holds the raw numbers.
- The PR description lists: files changed, new codes and weights, any unverified brand domains, and every number from §6.

**Out of scope:** retraining, new features or screens, rate limiting, iOS. Ask before touching anything else.
