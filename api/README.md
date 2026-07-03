# Cloud Threat Scoring API (Deliverable 3.2.2)

FastAPI service exposing the hybrid detection engine (rules + ML) over REST.

## Endpoints
| Method | Path | Purpose |
|---|---|---|
| POST | `/score/sms` | Score an SMS: risk 0-100, label, >= 3 reason codes |
| POST | `/score/url` | Score a single URL, returns SHA-256 indicator hash |
| POST | `/report` | User reports (scam / false_positive), PII hashed |
| GET | `/health` | Liveness probe |
| GET | `/stats` | Request counts + p50/p95 latency vs the 2 s target |
| GET | `/docs` | Auto-generated Swagger UI (OpenAPI) |

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
