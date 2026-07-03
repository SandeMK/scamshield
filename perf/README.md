# Performance & Propagation Tests (Assignment 2, section 14.6)

- `latency_test.py` — 100-request batch; reports p50/p95/max and % under
  the 2 s target (NFR-01, >= 95%).
- `propagation_test.py` — reports a fresh scam URL and measures how long
  until it influences scoring via INTEL_MATCH (NFR-07, < 30 s target).
  Requires the API running with SUPABASE_URL + SUPABASE_SERVICE_KEY set.

Run both against localhost during testing and against the deployed Render
URL for the report's final numbers:
    python latency_test.py --base-url https://<your-api>.onrender.com
    python propagation_test.py --base-url https://<your-api>.onrender.com
