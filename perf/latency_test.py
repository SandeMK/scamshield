"""
Section 14.6 performance test: batch of 100 scoring requests; report p50/p95,
max, and the percentage completing within the 2-second target (NFR-01).

Usage: python latency_test.py [--base-url URL] [--api-key KEY] [--n 100]
"""
import argparse
import statistics
import time

import requests

MESSAGES = [
    "URGENT: Your FNB account has been suspended. Verify at http://bit.ly/fnb-x",
    "SARS eFiling: pending refund R3,450. Confirm ID at sars-refunds.xyz/claim",
    "Hey, are we still on for lunch tomorrow at 1?",
    "Your parcel is held. Pay R45 at http://196.23.155.8/track",
    "FNB: R150.00 paid to Checkers from cheq acc. Ref 4521.",
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://localhost:8000")
    ap.add_argument("--api-key", default="demo-key")
    ap.add_argument("--n", type=int, default=100)
    args = ap.parse_args()
    headers = {"X-API-Key": args.api_key}
    base = args.base_url.rstrip("/")

    times = []
    for i in range(args.n):
        text = MESSAGES[i % len(MESSAGES)]
        t0 = time.perf_counter()
        r = requests.post(f"{base}/api/v1/score/sms", headers=headers,
                          json={"text": text}, timeout=10)
        r.raise_for_status()
        times.append((time.perf_counter() - t0) * 1000)

    times.sort()
    under = sum(1 for t in times if t < 2000) / len(times) * 100
    print(f"Requests : {len(times)}")
    print(f"p50      : {statistics.median(times):.1f} ms")
    print(f"p95      : {times[int(len(times) * 0.95)]:.1f} ms")
    print(f"max      : {max(times):.1f} ms")
    print(f"< 2 s    : {under:.1f}%  (target: >= 95%) -> "
          f"{'PASS' if under >= 95 else 'FAIL'}")


if __name__ == "__main__":
    main()
