# ScamShield — Measured Results

Recorded 6 July 2026 against the production deployment
(`https://scamshield-api-4ywt.onrender.com`, Render free tier, Supabase
threat DB connected). Client: macOS over residential connection.

## Success criteria vs measured (Assignment 2 §14.6, proposal §3.5)

| Criterion | Target | Measured | Verdict |
|---|---|---|---|
| Scoring latency (100-request batch, NFR-01) | >= 95% under 2 s | **100%** under 2 s (p50 770 ms, p95 1,214 ms, max 1,460 ms) | PASS |
| Intelligence propagation (NFR-07) | < 30 s | **0.8 s** (report -> INTEL_MATCH influencing scores) | PASS |
| Propagation effect | score influenced | 61 (MEDIUM_RISK) -> **90 (CRITICAL)** after user report | PASS |
| Detection F1 (ET-01), held-out 20% | >= 0.85 | **0.934** (precision 0.971, recall 0.899) | PASS |
| Dataset size (ET-01) | >= 500 labeled | 5,572 (UCI SMS Spam Collection) | PASS |
| Explanation codes | >= 3 per result | Guaranteed by design | PASS |
| Public threat feeds (§3.2.4) | >= 2, daily | URLhaus + OpenPhish, daily GitHub Actions cron | PASS |
| System integration | components interoperate | App + API + DB + feeds + fintech client verified end-to-end | PASS |

## Model selection (§14.5), 5-fold CV on training set

| Model | CV F1 (mean +/- std) |
|---|---|
| **RandomForest (selected)** | **0.9434 +/- 0.0054** |
| LogisticRegression | 0.9410 +/- 0.0183 |
| GradientBoosting | 0.9147 +/- 0.0156 |

Deployed model: `v1.0.0 (RandomForest)`, held-out F1 0.9338, confusion
matrix [[962, 4], [15, 134]] (ham, scam).

Note for discussion: under scikit-learn 1.8, LogisticRegression narrowly
won selection (0.941 vs 0.923); under 1.9 RandomForest won (0.943 vs
0.941). The two are statistically neck-and-neck; selection is empirical
per training run, and the model bundle is version-stamped (ET-05) so the
deployed artifact is always identifiable via /api/v1/health.

## Latency context

Local (same machine): ~3 ms p50. Production: 770 ms p50 — the difference
is network transit + TLS to the Render region and free-tier compute, not
model inference (inference budget ET-02: < 500 ms, comfortably met).
A keep-alive workflow pings /health every 10 minutes to prevent free-tier
cold starts (~30-60 s) from affecting measurements or demos.
