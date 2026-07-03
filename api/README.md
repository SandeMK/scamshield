# Cloud Threat Scoring API (Deliverable 3.2.2)

FastAPI service exposing the hybrid detection engine over REST.

Planned endpoints:
- `POST /score/sms` — score a full SMS message
- `POST /score/url` — score a single URL
- `POST /report` — user reports (scam / false positive)
- `GET /health` — liveness probe

Status: in progress.
