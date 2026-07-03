"""
ScamShield public threat-intelligence ingestion (Deliverable 3.2.4)

Fetches indicators from two open-source feeds, normalizes them, hashes them
(privacy by design, §3.2.3), and upserts them into the Supabase shared
threat-intelligence database via the ingest_indicators RPC.

Feeds:
    URLhaus  (abuse.ch)  - recent malicious URLs, CSV
    OpenPhish            - community phishing URLs, plain text

Runs on a daily schedule via GitHub Actions (.github/workflows/ingest.yml).

Env vars required:
    SUPABASE_URL          e.g. https://xyz.supabase.co
    SUPABASE_SERVICE_KEY  service role / secret key
"""

import csv
import hashlib
import io
import os
import sys
from urllib.parse import urlparse

import requests

URLHAUS_CSV = "https://urlhaus.abuse.ch/downloads/csv_recent/"
OPENPHISH_TXT = "https://openphish.com/feed.txt"

BATCH_SIZE = 500
MAX_PER_FEED = 5000  # keep well inside Supabase free-tier limits


def normalize(value: str) -> str:
    return value.strip().lower()


def hash_indicator(value: str) -> str:
    """Must match api/main.py:hash_indicator — sha256 of normalized value."""
    return hashlib.sha256(normalize(value).encode()).hexdigest()


def domain_of(url: str) -> str | None:
    try:
        netloc = urlparse(url if "://" in url else "http://" + url).netloc
        return netloc.split(":")[0] or None
    except ValueError:
        return None


def indicator_rows(url: str, source: str, threat_tag: str, reputation: int):
    """One URL yields a url-indicator and a domain-indicator."""
    yield {
        "indicator_hash": hash_indicator(url),
        "indicator_type": "url",
        "source": source,
        "threat_tag": threat_tag,
        "reputation": reputation,
    }
    dom = domain_of(url)
    if dom:
        yield {
            "indicator_hash": hash_indicator(dom),
            "indicator_type": "domain",
            "source": source,
            "threat_tag": threat_tag,
            "reputation": max(30, reputation - 20),  # domain evidence is weaker
        }


def fetch_urlhaus():
    print("Fetching URLhaus recent CSV ...")
    r = requests.get(URLHAUS_CSV, timeout=60)
    r.raise_for_status()
    rows = []
    reader = csv.reader(io.StringIO(r.text))
    for line in reader:
        if not line or line[0].startswith("#") or len(line) < 6:
            continue
        url, threat = line[2], line[5]
        rows.extend(indicator_rows(url, "urlhaus", threat or "malware", 90))
        if len(rows) >= MAX_PER_FEED:
            break
    print(f"  URLhaus indicators: {len(rows)}")
    return rows


def fetch_openphish():
    print("Fetching OpenPhish feed ...")
    r = requests.get(OPENPHISH_TXT, timeout=60)
    r.raise_for_status()
    rows = []
    for line in r.text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        rows.extend(indicator_rows(line, "openphish", "phishing", 85))
        if len(rows) >= MAX_PER_FEED:
            break
    print(f"  OpenPhish indicators: {len(rows)}")
    return rows


def upsert(supabase_url: str, key: str, rows: list) -> int:
    endpoint = f"{supabase_url}/rest/v1/rpc/ingest_indicators"
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    total = 0
    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i:i + BATCH_SIZE]
        resp = requests.post(endpoint, json={"batch": batch},
                             headers=headers, timeout=120)
        resp.raise_for_status()
        total += int(resp.text or 0)
        print(f"  upserted batch {i // BATCH_SIZE + 1}: {len(batch)} rows")
    return total


def main():
    supabase_url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    key = os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not supabase_url or not key:
        print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set.")
        sys.exit(1)

    rows, failures = [], []
    for fetch in (fetch_urlhaus, fetch_openphish):
        try:
            rows.extend(fetch())
        except Exception as exc:  # one feed failing must not kill the other
            failures.append(f"{fetch.__name__}: {exc}")
            print(f"  WARN {fetch.__name__} failed: {exc}")

    if not rows:
        print("ERROR: no indicators fetched from any feed.")
        sys.exit(1)

    # Deduplicate within this run (same URL can appear in both feeds).
    seen, unique = set(), []
    for row in rows:
        k = (row["indicator_hash"], row["indicator_type"])
        if k not in seen:
            seen.add(k)
            unique.append(row)

    print(f"Upserting {len(unique)} unique indicators ...")
    n = upsert(supabase_url, key, unique)
    print(f"DONE: {n} indicators ingested. Feed failures: {failures or 'none'}")


if __name__ == "__main__":
    main()
