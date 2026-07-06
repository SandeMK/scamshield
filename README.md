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

**Full visual documentation with diagrams: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**
(system overview, scoring sequence, intelligence propagation, database ER
diagram, and app structure — all rendered natively by GitHub.)

In one sentence: a Flutter app captures SMS, runs instant local checks, and
sends features to a FastAPI service that fuses rule-based and ML sub-scores
into an explained 0-100 risk score, enriched by a shared Supabase threat
database fed daily by URLhaus/OpenPhish and instantly by user reports.

## Repository structure → proposal deliverables

| Folder | Deliverable (proposal §) | Status |
|---|---|---|
| [`ml/`](ml/) | Hybrid detection engine — rules + ML (§3.2.2 core) | ✅ Done — F1 0.956 |
| [`api/`](api/) | Cloud Threat Scoring API (§3.2.2) | ✅ Done — ~3 ms latency |
| [`ingestion/`](ingestion/) | Public Threat Intelligence Integration (§3.2.4) + Shared DB schema (§3.2.3) | ✅ Done — daily automated ingestion |
| [`mobile-app/`](mobile-app/) | Flutter Mobile Application (§3.2.1, FR-01..FR-10) + In-App Analytics Dashboard (§3.2.5) | ✅ Source complete — build via `mobile-app/setup.sh` |
| [`fintech-client/`](fintech-client/) | Mock Fintech API Client (§3.2.6) | 🔜 Planned |

## Key results so far

| Success criterion | Target | Achieved |
|---|---|---|
| Scam detection F1-score | ≥ 0.85 | **0.942** held-out; model selection §14.5: LogReg 0.941 > RF 0.923 > GB 0.915 (5-fold CV) |
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

## Database note (design deviation)

Assignment 2 specified Cloud Firestore; the implementation uses Supabase
(PostgreSQL). Rationale: the indicator workload is relational (unique
hash+type upserts with `hit_count` increments and reputation merging via a
single SQL function), row-level security locks tables to the service key,
and the free tier requires no billing account. The documented design --
collections, fields, SHA-256 hashing, first/last-seen metadata -- maps
one-to-one onto the SQL schema in `ingestion/schema.sql`.

## Tech stack

Python 3.11 · scikit-learn · FastAPI · Supabase (PostgreSQL) · Flutter
(Dart) · URLhaus & OpenPhish feeds · GitHub Actions CI

## License

MIT — see [LICENSE](LICENSE).
