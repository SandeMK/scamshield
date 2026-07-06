"""
ScamShield Cloud Threat Scoring API (Deliverable 3.2.2)

RESTful service exposing the hybrid detection engine (rules + ML).

Endpoints:
    POST /score/sms   -> risk score, label, reason codes for an SMS message
    POST /score/url   -> risk score, label, reason codes for a single URL
    POST /report      -> user reports (scam / false positive)
    GET  /health      -> liveness probe
    GET  /stats       -> basic service metrics (requests, latency, detections)

Design notes:
- ThreatIntelClient is a pluggable hook: it currently returns no matches, and
  Component 3 (Supabase DB + feed ingestion) will implement real lookups.
  When an indicator matches, INTEL_MATCH is added as extra evidence, which
  raises the final score.
- Every scoring request is timed and logged (proposal: latency monitoring;
  success criterion: < 2 s response time).
"""

import hashlib
import logging
import os
import sys
import time
from collections import deque
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "ml"))
from score import ScamScorer  # noqa: E402
from features import extract_rules  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("scamshield.api")

MODEL_PATH = os.environ.get(
    "MODEL_PATH",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                 "ml", "model.joblib"),
)

API_KEY = os.environ.get("API_KEY", "demo-key")        # §12: API-key auth
ADMIN_KEY = os.environ.get("ADMIN_KEY", "admin-demo-key")
DOMAIN_MATCH_BONUS = 15   # weaker evidence: domain-level intel match
CRITICAL_FLOOR = 90       # §13.3: exact URL hash match in threat DB is critical


def require_api_key(x_api_key: str = Header(default="")):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


def require_admin_key(x_admin_key: str = Header(default="")):
    if x_admin_key != ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Admin key required")


# ---------------------------------------------------------------------------
# Threat intelligence hook (implemented for real in Component 3)
# ---------------------------------------------------------------------------

def hash_indicator(value: str) -> str:
    """Privacy-preserving indicator representation (proposal 3.2.3)."""
    return hashlib.sha256(value.strip().lower().encode()).hexdigest()


class ThreatIntelClient:
    """Fallback stub used when Supabase env vars are absent (offline dev)."""

    def lookup(self, url: str) -> Optional[dict]:
        return None

    def record_report(self, report: dict) -> None:
        log.info("REPORT %s", report)


class SupabaseThreatIntelClient(ThreatIntelClient):
    """Live client for the shared threat-intelligence DB (Component 3).

    Checks the full URL hash first (strong evidence), then the domain hash
    (weaker evidence). Requires SUPABASE_URL + SUPABASE_SERVICE_KEY.
    """

    def __init__(self, base_url: str, key: str):
        import httpx
        self._rest = f"{base_url.rstrip('/')}/rest/v1"
        self._client = httpx.Client(
            headers={"apikey": key, "Authorization": f"Bearer {key}"},
            timeout=1.5,  # keep total response well under the 2 s budget
        )

    def ping(self) -> bool:
        try:
            r = self._client.get(f"{self._rest}/indicators",
                                 params={"select": "id", "limit": "1"})
            return r.status_code == 200
        except Exception:
            return False

    def _query(self, indicator_hash: str, indicator_type: str) -> Optional[dict]:
        try:
            r = self._client.get(
                f"{self._rest}/indicators",
                params={
                    "indicator_hash": f"eq.{indicator_hash}",
                    "indicator_type": f"eq.{indicator_type}",
                    "select": "source,threat_tag,reputation,hit_count",
                    "limit": "1",
                },
            )
            r.raise_for_status()
            rows = r.json()
            return rows[0] if rows else None
        except Exception as exc:  # DB unavailability must never block scoring
            log.warning("intel lookup failed: %s", exc)
            return None

    def lookup(self, url: str) -> Optional[dict]:
        from urllib.parse import urlparse
        match = self._query(hash_indicator(url), "url")
        if match:
            return {**match, "match_type": "url"}
        netloc = urlparse(url if "://" in url else "http://" + url).netloc
        domain = netloc.split(":")[0]
        match = self._query(hash_indicator(domain), "domain") if domain else None
        return {**match, "match_type": "domain"} if match else None

    def record_report(self, report: dict) -> None:
        try:
            self._client.post(f"{self._rest}/reports", json={
                "report_type": report["report_type"],
                "text_hash": report.get("text_hash"),
                "url_hash": report.get("url_hash"),
            }).raise_for_status()
            batch = report.get("indicator_batch") or []
            if batch:
                self._client.post(f"{self._rest}/rpc/ingest_indicators",
                                  json={"batch": batch}).raise_for_status()
                log.info("report ingested %d indicators", len(batch))
        except Exception as exc:
            log.warning("report persist failed: %s", exc)


# ---------------------------------------------------------------------------
# API models
# ---------------------------------------------------------------------------

class SmsRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)
    sender: Optional[str] = Field(None, max_length=30)


class UrlRequest(BaseModel):
    url: str = Field(..., min_length=4, max_length=500)


class ReportRequest(BaseModel):
    text: Optional[str] = Field(None, max_length=2000)
    url: Optional[str] = Field(None, max_length=500)
    report_type: str = Field(..., pattern="^(scam|false_positive)$")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="ScamShield Threat Scoring API",
    version="1.0.0",
    description="Hybrid (rules + ML) scam detection for SMS and URLs. "
                "All /api/v1 endpoints except /health require the X-API-Key header.",
)

scorer = ScamScorer(MODEL_PATH)

_supabase_url = os.environ.get("SUPABASE_URL", "")
_supabase_key = os.environ.get("SUPABASE_SERVICE_KEY", "")
if _supabase_url and _supabase_key:
    intel = SupabaseThreatIntelClient(_supabase_url, _supabase_key)
    log.info("Threat intel: Supabase client active (%s)", _supabase_url)
else:
    intel = ThreatIntelClient()
    log.info("Threat intel: stub client (no SUPABASE_URL configured)")

_stats = {
    "requests_total": 0,
    "high_risk_detections": 0,
    "reports_received": 0,
}
_latencies_ms = deque(maxlen=1000)


def _apply_intel(result: dict) -> dict:
    """Check extracted URLs against threat intelligence (§13.3).

    Exact URL hash match = critical: score floors at 90. Domain-only match
    is weaker corroborating evidence: +15, capped at 100.
    """
    for url in result.get("urls", []):
        match = intel.lookup(url)
        if not match:
            continue
        if match.get("match_type") == "url":
            result["risk_score"] = max(result["risk_score"], CRITICAL_FLOOR)
            detail = ("Exact link match in the shared threat intelligence "
                      f"database (source: {match.get('source', 'unknown')})")
        else:
            result["risk_score"] = min(100, result["risk_score"] + DOMAIN_MATCH_BONUS)
            detail = ("Link domain matches a known malicious indicator "
                      f"(source: {match.get('source', 'unknown')})")
        result["explanation_codes"].insert(0, {"code": "INTEL_MATCH", "detail": detail})
        from score import _label
        result["classification"] = _label(result["risk_score"])
        break
    return result


def _finalize(result: dict, started: float) -> dict:
    latency_ms = round((time.perf_counter() - started) * 1000, 2)
    _latencies_ms.append(latency_ms)
    _stats["requests_total"] += 1
    if result["classification"] in ("HIGH_RISK", "CRITICAL"):
        _stats["high_risk_detections"] += 1
    result["latency_ms"] = latency_ms
    log.info("SCORE risk=%s classification=%s latency=%sms",
             result["risk_score"], result["classification"], latency_ms)
    return result


@app.post("/api/v1/score/sms", dependencies=[Depends(require_api_key)])
def score_sms(req: SmsRequest):
    started = time.perf_counter()
    result = scorer.score(req.text)
    result = _apply_intel(result)
    return _finalize(result, started)


@app.post("/api/v1/score/url", dependencies=[Depends(require_api_key)])
def score_url(req: UrlRequest):
    started = time.perf_counter()
    # Score the URL both as text (rules like shorteners fire on it) and
    # against threat intelligence.
    result = scorer.score(req.url)
    rules = extract_rules(req.url)
    if req.url not in result["urls"]:
        result["urls"] = list({*result["urls"], req.url})
    result = _apply_intel(result)
    result["indicator_hash"] = hash_indicator(req.url)
    return _finalize(result, started)


@app.post("/api/v1/report", dependencies=[Depends(require_api_key)])
def report(req: ReportRequest):
    payload = {
        "report_type": req.report_type,
        "text_hash": hash_indicator(req.text) if req.text else None,
        "url_hash": hash_indicator(req.url) if req.url else None,
        "received_at": time.time(),
    }

    # NFR-07 / FR-06: confirmed-scam reports become shared indicators so
    # they influence scoring for all users (target: within 30 s).
    if req.report_type == "scam":
        from urllib.parse import urlparse
        urls = set(extract_rules(req.text).urls if req.text else [])
        if req.url:
            urls.add(req.url)
        batch = []
        for u in urls:
            batch.append({"indicator_hash": hash_indicator(u),
                          "indicator_type": "url",
                          "source": "user_report",
                          "threat_tag": "user_reported",
                          "reputation": 70})
            netloc = urlparse(u if "://" in u else "http://" + u).netloc
            domain = netloc.split(":")[0]
            if domain:
                batch.append({"indicator_hash": hash_indicator(domain),
                              "indicator_type": "domain",
                              "source": "user_report",
                              "threat_tag": "user_reported",
                              "reputation": 50})
        payload["indicator_batch"] = batch

    intel.record_report(payload)
    _stats["reports_received"] += 1
    payload.pop("indicator_batch", None)  # keep the response lean
    return {"status": "received", "report": payload}


@app.get("/api/v1/health")
def health():
    db_connected = None  # unknown when running with the stub client
    if isinstance(intel, SupabaseThreatIntelClient):
        db_connected = intel.ping()
    return {
        "status": "ok",
        "model_version": scorer.model_version + f" ({scorer.model_name})",
        "db_connected": db_connected,
    }


@app.post("/api/v1/intel/ingest", dependencies=[Depends(require_admin_key)])
def trigger_ingest():
    """Manually trigger feed ingestion (§12) — also runs on the daily cron."""
    import threading

    def _run():
        import subprocess
        script = os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "ingestion", "ingest.py")
        subprocess.run([sys.executable, script], check=False)

    threading.Thread(target=_run, daemon=True).start()
    return {"status": "ingestion_started"}


@app.get("/api/v1/analytics/summary", dependencies=[Depends(require_api_key)])
def analytics_summary():
    lat = sorted(_latencies_ms)
    return {
        **_stats,
        "latency_ms_p50": lat[len(lat) // 2] if lat else None,
        "latency_ms_p95": lat[int(len(lat) * 0.95)] if lat else None,
        "latency_target_s": 2.0,
    }
