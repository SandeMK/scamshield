# Cloud Threat Scoring API (Deliverable 3.2.2)

FastAPI service exposing the hybrid detection engine (rules + ML) over REST.

## Endpoints (Assignment 2, section 12)
| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | `/api/v1/score/sms` | API key | Hybrid scoring: risk 0-100, classification, >= 3 explanation codes, ml_confidence, rule_sub_score, model_version |
| POST | `/api/v1/score/url` | API key | Score a single URL; returns SHA-256 indicator hash |
| POST | `/api/v1/report` | API key | Scam / false-positive reports, indicators hashed |
| GET | `/api/v1/analytics/summary` | API key | Scan counts + p50/p95 latency for the dashboard |
| GET | `/api/v1/health` | none | Status, active model version, DB connectivity |
| POST | `/api/v1/intel/ingest` | Admin key | Manually trigger feed ingestion (also daily cron) |
| GET | `/docs` | none | Auto-generated Swagger UI (OpenAPI) |

Auth: `X-API-Key` header (env `API_KEY`, default `demo-key` for dev);
admin endpoint uses `X-Admin-Key` (env `ADMIN_KEY`).
Classification labels: SAFE, LOW_RISK, MEDIUM_RISK, HIGH_RISK, CRITICAL.
Hybrid fusion: 60% ML + 40% rules with the critical override (section 13.3);
an exact URL match in the threat DB floors the score at 90 (CRITICAL).

## Run locally
```bash
pip install -r requirements.txt
uvicorn main:app --reload        # from api/
# Swagger UI: http://localhost:8000/docs
```

## Run tests
```bash
python -m pytest tests/ -v
```

## Deploy (container)
```bash
# from repo root
docker build -f api/Dockerfile -t scamshield-api .
docker run -p 8080:8080 scamshield-api
```
Works on Google Cloud Run or Render free tiers.

## Measured performance
End-to-end scoring latency ~3 ms locally (p50 1.1 ms server-side) —
success criterion of < 2 s met with large margin.

## Threat intelligence hook
`ThreatIntelClient.lookup()` is a stub returning no matches; Component 3
(Supabase DB + URLhaus/OpenPhish ingestion) implements it. On a match the
API adds an `INTEL_MATCH` reason and boosts the risk score.
