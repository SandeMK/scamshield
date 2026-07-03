"""
ScamShield Fintech API Client (Deliverable 3.2.6, FR-09, US-08)

Simulates how a financial institution would consume the ScamShield scoring
API inside its own fraud-detection workflow:

  1. The "bank" holds a queue of customer-forwarded SMS messages.
  2. Each is submitted to POST /api/v1/score/sms with the bank's API key.
  3. The structured JSON response drives a business decision:
       CRITICAL / HIGH_RISK  -> block + alert fraud team
       MEDIUM_RISK           -> queue for analyst review
       LOW_RISK / SAFE       -> no action
  4. Confirmed scams are reported back via POST /api/v1/report,
     enriching the shared threat intelligence network.

Usage:
    python client.py                          # against http://localhost:8000
    python client.py --base-url https://scamshield-api.onrender.com
    python client.py --api-key <key>
"""

import argparse
import json
import sys
import time

import requests

CUSTOMER_QUEUE = [
    ("+27831234567", "SARS eFiling: You have a pending refund of R3,450. "
                     "Confirm your ID number at http://sars-refunds.xyz/claim"),
    ("+27829990001", "URGENT: Your FNB account has been suspended. Verify now "
                     "at http://bit.ly/fnb-secure or lose access."),
    ("+27761112223", "FNB: R150.00 paid to Checkers from cheq acc. Ref 4521."),
    ("29123",        "Your parcel is held at customs. Pay the R45 release fee "
                     "at http://196.23.155.8/track to avoid return."),
    ("+27845556667", "Hey, are we still on for lunch tomorrow at 1?"),
]


def decide(classification: str) -> str:
    if classification in ("CRITICAL", "HIGH_RISK"):
        return "BLOCK + ALERT FRAUD TEAM"
    if classification == "MEDIUM_RISK":
        return "QUEUE FOR ANALYST REVIEW"
    return "NO ACTION"


def main():
    ap = argparse.ArgumentParser(description="ScamShield fintech client demo")
    ap.add_argument("--base-url", default="http://localhost:8000")
    ap.add_argument("--api-key", default="demo-key")
    args = ap.parse_args()

    headers = {"X-API-Key": args.api_key, "Content-Type": "application/json"}
    base = args.base_url.rstrip("/")

    print("=" * 72)
    print("DemoBank Fraud Desk -> ScamShield Threat Scoring API")
    print("=" * 72)

    # Health / contract check first (US-08: structured, documented API)
    health = requests.get(f"{base}/api/v1/health", timeout=10).json()
    print(f"API status: {health.get('status')} | "
          f"model: {health.get('model_version')} | "
          f"DB connected: {health.get('db_connected')}\n")

    latencies, blocked = [], 0
    for sender, text in CUSTOMER_QUEUE:
        t0 = time.perf_counter()
        resp = requests.post(f"{base}/api/v1/score/sms",
                             headers=headers,
                             json={"text": text, "sender": sender},
                             timeout=10)
        rtt = (time.perf_counter() - t0) * 1000
        latencies.append(rtt)

        if resp.status_code != 200:
            print(f"[ERROR {resp.status_code}] {resp.text}")
            continue

        r = resp.json()
        action = decide(r["classification"])
        print(f"From {sender:<14} risk={r['risk_score']:>3} "
              f"{r['classification']:<12} rtt={rtt:>6.1f}ms  -> {action}")
        for code in r["explanation_codes"][:3]:
            print(f"    - {code['code']}: {code['detail']}")

        if action.startswith("BLOCK"):
            blocked += 1
            requests.post(f"{base}/api/v1/report", headers=headers,
                          json={"text": text, "report_type": "scam"},
                          timeout=10)
            print("    -> reported to shared threat intelligence network")
        print()

    print("-" * 72)
    print(f"Processed {len(CUSTOMER_QUEUE)} messages | blocked {blocked} | "
          f"avg round-trip {sum(latencies)/len(latencies):.1f} ms | "
          f"max {max(latencies):.1f} ms (target < 2000 ms)")
    print("Interoperability demonstrated: external system consumed the "
          "scoring API and contributed intelligence back.")


if __name__ == "__main__":
    sys.exit(main())
