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

from fastapi import FastAPI
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

INTEL_MATCH_BONUS = 25  # score uplift when an indicator is a known-bad match


# ---------------------------------------------------------------------------
# Threat intelligence hook (implemented for real in Component 3)
# ---------------------------------------------------------------------------

def hash_indicator(value: str) -> str:
    """Privacy-preserving indicator representation (proposal 3.2.3)."""
    return hashlib.sha256(value.strip().lower().encode()).hexdigest()


class ThreatIntelClient:
    """Stub client. Component 3 replaces lookup() with a Supabase query."""

    def lookup(self, url: str) -> Optional[dict]:
        return None  # no DB yet

    def record_report(self, report: dict) -> None:
        log.info("REPORT %s", report)


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
    version="0.2.0",
    description="Hybrid (rules + ML) scam detection for SMS and URLs.",
)

scorer = ScamScorer(MODEL_PATH)
intel = ThreatIntelClient()

_stats = {
    "requests_total": 0,
    "high_risk_detections": 0,
    "reports_received": 0,
}
_latencies_ms = deque(maxlen=1000)


def _apply_intel(result: dict) -> dict:
    """Check extracted URLs against threat intelligence; boost if matched."""
    for url in result.get("urls", []):
        match = intel.lookup(url)
        if match:
            result["risk_score"] = min(100, result["risk_score"] + INTEL_MATCH_BONUS)
            result["reasons"].insert(0, {
                "code": "INTEL_MATCH",
                "description": "Link matches a known malicious indicator "
                               "in the shared threat intelligence database",
            })
            break
    return result


def _finalize(result: dict, started: float) -> dict:
    latency_ms = round((time.perf_counter() - started) * 1000, 2)
    _latencies_ms.append(latency_ms)
    _stats["requests_total"] += 1
    if result["label"] == "HIGH_RISK":
        _stats["high_risk_detections"] += 1
    result["latency_ms"] = latency_ms
    log.info("SCORE risk=%s label=%s latency=%sms",
             result["risk_score"], result["label"], latency_ms)
    return result


@app.post("/score/sms")
def score_sms(req: SmsRequest):
    started = time.perf_counter()
    result = scorer.score(req.text)
    result = _apply_intel(result)
    return _finalize(result, started)


@app.post("/score/url")
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


@app.post("/report")
def report(req: ReportRequest):
    payload = {
        "report_type": req.report_type,
        "text_hash": hash_indicator(req.text) if req.text else None,
        "url_hash": hash_indicator(req.url) if req.url else None,
        "received_at": time.time(),
    }
    intel.record_report(payload)
    _stats["reports_received"] += 1
    return {"status": "received", "report": payload}


@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": scorer is not None}


@app.get("/stats")
def stats():
    lat = sorted(_latencies_ms)
    return {
        **_stats,
        "latency_ms_p50": lat[len(lat) // 2] if lat else None,
        "latency_ms_p95": lat[int(len(lat) * 0.95)] if lat else None,
        "latency_target_s": 2.0,
    }
