# ScamShield

**A Mobile-First Cloud-Powered Threat Intelligence Network for Detecting SMS
Phishing (Smishing) Campaigns in South Africa**

> ISJ107V Integrated Software Project — Tshwane University of Technology,
> Faculty of ICT, Computer Science Department
> Student: Philasande Makhubela (216432363)

South Africa has seen a sharp rise in SMS phishing that impersonates banks,
SARS, and courier services. ScamShield detects suspicious SMS messages and
embedded URLs in near real time, assigns an explainable 0–100 risk score with
at least three reason codes, and shares newly discovered scam indicators
across all users through a cloud threat-intelligence network.

## Architecture

```
┌─────────────────┐   REST    ┌──────────────────────┐
│  Android App    │──────────▶│  Cloud Scoring API   │
│  (SMS listener, │◀──────────│  (FastAPI)           │
│  local rules,   │  score +  │  rules + ML hybrid   │
│  dashboard)     │  reasons  └──────┬───────────────┘
└─────────────────┘                  │
        │ report scams               ▼
        ▼                    ┌──────────────────────┐
┌─────────────────┐          │ Threat Intel DB      │
│ Mock Fintech    │─────────▶│ (Supabase/Postgres,  │
│ API Client      │   REST   │ hashed indicators)   │
└─────────────────┘          └──────▲───────────────┘
                                    │ daily ingestion
                     ┌──────────────┴───────┐
                     │ Public feeds:        │
                     │ URLhaus, OpenPhish   │
                     └──────────────────────┘
```

## Repository structure → proposal deliverables

| Folder | Deliverable (proposal §) | Status |
|---|---|---|
| [`ml/`](ml/) | Hybrid detection engine — rules + ML (§3.2.2 core) | ✅ Done — F1 0.956 |
| [`api/`](api/) | Cloud Threat Scoring API (§3.2.2) | ✅ Done — ~3 ms latency |
| [`ingestion/`](ingestion/) | Public Threat Intelligence Integration (§3.2.4) + Shared DB schema (§3.2.3) | 🔜 Planned |
| [`android/`](android/) | Android Mobile Application (§3.2.1) + In-App Analytics Dashboard (§3.2.5) | 🔜 Planned |
| [`mock-fintech-client/`](mock-fintech-client/) | Mock Fintech API Client (§3.2.6) | 🔜 Planned |

## Key results so far

| Success criterion | Target | Achieved |
|---|---|---|
| Scam detection F1-score | ≥ 0.85 | **0.956** (held-out), 0.945 ± 0.010 (5-fold CV) |
| Labeled dataset size | ≥ 500 | 5,572 (UCI SMS Spam Collection) |
| Explanation reason codes | ≥ 3 per result | Guaranteed by design |
| Scoring response time | < 2 s | ~3 ms locally (p50 1.1 ms) |

## Quick start (ML component)

```bash
git clone https://github.com/SandeMK/scamshield.git
cd scamshield/ml
pip install -r requirements.txt
python train.py    # auto-downloads dataset, trains, evaluates, saves model
python score.py    # demo on realistic SA smishing samples
```

## Tech stack

Python 3.11 · scikit-learn · FastAPI · Supabase (PostgreSQL) · Kotlin /
Android Studio · URLhaus & OpenPhish feeds · GitHub Actions CI

## License

MIT — see [LICENSE](LICENSE).
