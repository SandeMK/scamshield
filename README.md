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

## Running the system

### 0. First-time setup
```bash
git clone https://github.com/SandeMK/scamshield.git
cd scamshield
pip install -r api/requirements.txt      # covers ml/ + api/ + tests
pip install -r ingestion/requirements.txt
```

### 1. Scoring API (start this first — everything talks to it)
```bash
cd api
uvicorn main:app --host 0.0.0.0 --port 8000
```
- Swagger UI: http://localhost:8000/docs · health: http://localhost:8000/api/v1/health
- Dev API key: `demo-key` (override with env `API_KEY`; admin: `ADMIN_KEY`)
- To enable shared threat-intel lookups and report propagation, set env
  vars **before** starting:
  ```bash
  export SUPABASE_URL=https://<project-id>.supabase.co
  export SUPABASE_SERVICE_KEY=<sb_secret_...>
  ```
  Without them the API runs with a stub intel client (scoring still works).

### 2. Mobile app
```bash
cd mobile-app
./setup.sh                 # first time only: flutter create + install source
cd app && flutter run      # emulator running or device connected
```
- Emulator: default Base URL `http://10.0.2.2:8000` works as-is.
- Physical device: in the app's Settings tab set Base URL to your
  machine's LAN IP, e.g. `http://192.168.1.23:8000`
  (find it: `ipconfig getifaddr en0` on macOS, `ipconfig` on Windows);
  phone and machine must be on the same Wi-Fi.
- Requires Flutter >= 3.22.

### 3. ML: retrain / evaluate the model
```bash
cd ml
python train.py    # auto-downloads dataset, 3-model CV selection, saves model.joblib
python score.py    # demo scoring on realistic SA smishing samples
```
Retrain whenever your local scikit-learn version differs from the one that
produced the committed `model.joblib` (fixes InconsistentVersionWarning).

### 4. Fintech interoperability demo (API must be running)
```bash
python fintech-client/client.py                          # against localhost
python fintech-client/client.py --base-url https://<deployed-host> --api-key <key>
```

### 5. Threat feed ingestion
Runs automatically daily via GitHub Actions (04:00 UTC), or trigger manually:
- GitHub -> Actions -> "Threat Feed Ingestion" -> Run workflow, or
- `curl -X POST -H "X-Admin-Key: <admin-key>" <api-host>/api/v1/intel/ingest`, or
- locally: `SUPABASE_URL=... SUPABASE_SERVICE_KEY=... python ingestion/ingest.py`

### 6. Tests
```bash
(cd ml && python -m pytest tests/ -v)         # detection engine
(cd api && python -m pytest tests/ -v)        # API contract + auth
(cd ingestion && python -m pytest tests/ -v)  # normalization + hashing
```

### 7. Performance measurements (§14.6)
```bash
python perf/latency_test.py --base-url http://localhost:8000       # NFR-01
python perf/propagation_test.py --base-url http://localhost:8000   # NFR-07, needs Supabase env
```

### 8. Deploy to Render (free tier)
Render dashboard -> New -> Blueprint -> select this repo (`render.yaml`
auto-configures) -> set env values: `API_KEY`, `ADMIN_KEY`, `SUPABASE_URL`,
`SUPABASE_SERVICE_KEY`. Then set repo variable `API_BASE_URL` so the
keep-alive workflow prevents free-tier cold starts.

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
