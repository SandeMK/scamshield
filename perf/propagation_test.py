"""
Section 14.6 / NFR-07 propagation test: report a fresh scam URL, then poll
scoring until INTEL_MATCH appears. Target: < 30 seconds.

Requires the API to be running WITH Supabase configured (env vars set),
otherwise reports never reach the shared database.

Usage: python propagation_test.py [--base-url URL] [--api-key KEY]
"""
import argparse
import time
import uuid

import requests


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://localhost:8000")
    ap.add_argument("--api-key", default="demo-key")
    args = ap.parse_args()
    headers = {"X-API-Key": args.api_key}
    base = args.base_url.rstrip("/")

    # Unique URL so no earlier indicator can match.
    url = f"http://scam-{uuid.uuid4().hex[:10]}.example-fraud.xyz/login"
    text = f"URGENT: verify your account at {url}"

    before = requests.post(f"{base}/api/v1/score/sms", headers=headers,
                           json={"text": text}, timeout=10).json()
    codes = [c["code"] for c in before["explanation_codes"]]
    assert "INTEL_MATCH" not in codes, "URL matched before reporting?!"
    print(f"Baseline score: {before['risk_score']} ({before['classification']})")

    t0 = time.perf_counter()
    requests.post(f"{base}/api/v1/report", headers=headers,
                  json={"url": url, "report_type": "scam"},
                  timeout=10).raise_for_status()
    print("Reported as scam; polling for propagation ...")

    while True:
        elapsed = time.perf_counter() - t0
        r = requests.post(f"{base}/api/v1/score/sms", headers=headers,
                          json={"text": text}, timeout=10).json()
        if any(c["code"] == "INTEL_MATCH" for c in r["explanation_codes"]):
            print(f"Propagated in {elapsed:.1f} s "
                  f"(target < 30 s) -> {'PASS' if elapsed < 30 else 'FAIL'}")
            print(f"Score after: {r['risk_score']} ({r['classification']})")
            return
        if elapsed > 120:
            print("FAIL: no propagation within 120 s")
            return
        time.sleep(2)


if __name__ == "__main__":
    main()
