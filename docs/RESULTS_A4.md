# ScamShield — Assignment 4 Measured Results

Recorded 28 October 2026 against the production deployment
(`https://scamshield-api-4ywt.onrender.com`, Render free tier, Supabase
threat DB connected) after merging PR #3 (`1d3b7ea`, A4 prototype fixes).
Client: macOS over a residential connection. Raw tool output is reproduced
verbatim in the fenced blocks.

## Deployed version

```
GET /api/v1/health
{"status":"ok","model_version":"v1.0.0 (RandomForest)","db_connected":true}
```

Model bundle: RandomForest `v1.0.0`, trained and pinned under
scikit-learn 1.9.0 (`ml/requirements.txt`). CI installs `scikit-learn-1.9.0`
with no `InconsistentVersionWarning`.

## Success criteria vs measured

| Criterion | Target | A3 | A4 (this run) | Verdict |
|---|---|---|---|---|
| Scoring latency, 100 requests (NFR-01) | >= 95% under 2 s | 100% (p50 770 ms, p95 1,214 ms) | **100%** (p50 814 ms, p95 1,254 ms, max 1,537 ms) | PASS |
| Intelligence propagation (NFR-07) | < 30 s | 0.8 s | **0.9 s median** (1.5 / 0.9 / 0.8 s) | PASS |
| Propagation effect | score influenced | 61 -> 90 | **61 (MEDIUM_RISK) -> 90 (CRITICAL)** | PASS |
| Detection F1, held-out 20% (ET-01) | >= 0.85 | 0.934 | **0.9338** (unchanged, no retraining) | PASS |

## 1. Latency (`perf/latency_test.py`)

```
Requests : 100
p50      : 813.6 ms
p95      : 1253.7 ms
max      : 1537.0 ms
< 2 s    : 100.0%  (target: >= 95%) -> PASS
```

## 2. Propagation (`perf/propagation_test.py`, 3 runs)

```
=== run 1 (2026-10-28T19:25:52Z)
Baseline score: 61 (MEDIUM_RISK)
Reported as scam; polling for propagation ...
Propagated in 1.5 s (target < 30 s) -> PASS
Score after: 90 (CRITICAL)
=== run 2 (2026-10-28T19:25:56Z)
Baseline score: 61 (MEDIUM_RISK)
Reported as scam; polling for propagation ...
Propagated in 0.9 s (target < 30 s) -> PASS
Score after: 90 (CRITICAL)
=== run 3 (2026-10-28T19:25:58Z)
Baseline score: 61 (MEDIUM_RISK)
Reported as scam; polling for propagation ...
Propagated in 0.8 s (target < 30 s) -> PASS
Score after: 90 (CRITICAL)
```

Median **0.9 s**.

**Finding: reporting was silently broken from 24 Sep to 28 Oct.** Six
earlier runs that day (19:04–19:18Z) all failed (`no propagation within
120 s`). The FR-14 profile feature (24 Sep) made `POST /report` write a
`device_id` column, but that part of `ingestion/schema.sql` had never been
applied to the live DB. Every insert into `reports` was rejected, and
because the indicator batch is written in the same `try` block, no
user-reported indicator reached the DB either. The API logged a warning
and still returned 200. Applying the migration fixed it; the passing runs
above were taken straight afterwards. The Supabase project also had to be
restored after GitHub auto-disabled the daily workflows for inactivity.

## 3. Model: held-out evaluation (`ml/evaluate.py`, no refit)

```
Model    : RandomForest v1.0.0 (scikit-learn 1.9.0)
Held-out : 1115 messages (20%, stratified, seed 42)
F1-score : 0.9338
Precision: 0.9710
Recall   : 0.8993
Accuracy : 0.9830
Confusion matrix [rows=true, cols=pred] (ham, scam):
  [[962, 4], [15, 134]]
```

The A4 rules sit after the model and never change its inputs.
`ml/tests/test_model_regression.py` proves this: `full_feature_vector()` for
all 5,572 UCI messages is bit-identical to a snapshot taken before the
change, and the results above are pinned.

## 4. Before / after scores (deployed API)

"Before" is the pre-A4 code (commit `e62f461`, same model). The SARS score
of 63 with `urls: []` was also observed on the live A3 deployment shortly
before the redeploy. "After" is this deployment.

| Message | Before | After | New code |
|---|---|---|---|
| `SARS refund of R3,450 approved. Claim now: bit.ly/sars-rf` | 63 MEDIUM_RISK, `urls: []` | **95 CRITICAL**, `urls: ["http://bit.ly/sars-rf"]` | `BRAND_LINK_MISMATCH` (+20) |
| `FNB: Your account is on hold. Verify your details at fnb-secure-za.com/login within 24 hrs` | 66 MEDIUM_RISK | **90 CRITICAL** | `BRAND_LOOKALIKE_DOMAIN` (+30) |
| `Your FNB OTP is 482913. Never share it with anyone.` | 41 MEDIUM_RISK | 41 MEDIUM_RISK | none |
| `SARS: Your eFiling return has been received. Visit https://www.sars.gov.za for status.` | 52 MEDIUM_RISK | 52 MEDIUM_RISK | none |
| `Capitec: R250.00 paid to Checkers. Avail bal R1,204.33` | 23 LOW_RISK | 23 LOW_RISK | none |
| `Hey, are we still on for lunch tomorrow at 1?` | 0 SAFE | 0 SAFE | none |

The four legitimate responses are identical to the pre-change baseline in
every field except `latency_ms` (`ml/tests/fixtures/legit_baseline.json`).

### Scheme-less link reported then rescanned (live, unique throwaway link)

```
before report (bare)          42 MEDIUM_RISK  intel=False  urls=['http://bit.ly/a4-3aa61424']
after report: bare            90 CRITICAL     intel=True  urls=['http://bit.ly/a4-3aa61424']
after report: http://         90 CRITICAL     intel=True  urls=['http://bit.ly/a4-3aa61424']
after report: https://        90 CRITICAL     intel=True  urls=['https://bit.ly/a4-3aa61424']
other bit.ly link (A2)        16 SAFE         intel=False  urls=['http://bit.ly/77c35218']
```

A report of one `bit.ly` link matches that link however it is written, and
does not raise other `bit.ly` links (no shortener domain indicator).

## 5. Tests

| Suite | Before A4 | After A4 | Where |
|---|---|---|---|
| ML (`ml/tests`) | 5 | **49 passed** | CI + local |
| API (`api/tests`) | 17 | **24 passed** | CI + local |
| Ingestion (`ingestion/tests`, incl. UT-06 hash) | 4 | **7 passed** (4 when measured + 3 URLhaus API tests) | CI + local |
| Flutter (`mobile-app/test/widget_test.dart`) | 35 | **40 passed** | local only (not in CI) |

## Known limitations and trade-offs (for discussion)

- **Rule-only CRITICAL.** The brand rules use the brief's weights (+30/+20).
  On both scam samples they lift the rule sub-score to >= 90, which triggers
  the existing critical override, so a brand rule alone can now produce
  CRITICAL, and with it a Guardian Alert SMS, without ML or intel evidence.
- **Explanation-code cap.** `INTEL_MATCH` is inserted after `score.py` trims
  to 6 codes, so an intel-matched response can carry 7. On the SARS sample
  the cap now drops `ML_PHISHING_PATTERN`; the brand code is placed first so
  it survives.
- **URLhaus feed moved behind authentication.** The keyless
  `https://urlhaus.abuse.ch/downloads/csv_recent/` returned **410 Gone** on
  28 Oct 2026, so only OpenPhish (now redirected to GitHub) was being
  ingested. `ingestion/ingest.py` now uses abuse.ch's authenticated API
  (`v1/urls/recent`, up to 1,000 URLs from the last 3 days per run), which
  needs a free Auth-Key stored as the `URLHAUS_AUTH_KEY` repo secret.
- **Shared API key.** The repository is public and the mobile app ships its
  API key in source, so anyone can call `/report` and add indicators. That
  could raise any URL to CRITICAL for all users. Acceptable for a sideloaded
  demo; production would need per-device credentials and report moderation
  or rate limiting.
- **Brand keyword hosts.** Short host keywords (`fnb`, `mtn`, `absa`, `sars`)
  can match unrelated hosts that happen to contain them. These rules only
  fire when a link is present.
- **Unverified brand domain.** `thecourierguy.co.za` sits behind a
  Cloudflare challenge and was confirmed only through third-party listings.

## Still to record (student)

- Render build log for `1d3b7ea`: `scikit-learn==1.9.0` installed and no
  `InconsistentVersionWarning` on model load.
- Release APK on the Samsung S938B: device tests ST-01 to ST-07.
- Screenshots listed in `plans/A4_BUILD_BRIEF.md` §7.
