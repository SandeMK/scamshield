# Fintech API Client (Deliverable 3.2.6, FR-09, US-08)

Simulated third-party client showing how a financial institution consumes
the ScamShield scoring API inside a fraud-detection workflow: it scores a
queue of customer-forwarded SMS messages, applies business rules
(block / review / no action), and reports confirmed scams back to the
shared threat intelligence network.

## Run it
```bash
pip install requests
# with the API running locally (cd api && uvicorn main:app):
python client.py
# or against the deployed API:
python client.py --base-url https://<your-api-host> --api-key <key>
```

Output includes per-message risk score, classification, explanation codes,
round-trip latency vs the 2 s target, and the resulting business decision.
