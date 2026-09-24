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
import secrets
import sys
import time
from collections import deque
from datetime import datetime, timezone
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

DEFAULT_NOTIFICATION_PREFS = {
    "alert_threshold": "MEDIUM_RISK",
    "retroactive_updates": True,
    "report_outcomes": True,
    "digest_frequency": "off",
}
RECOVERY_CODE_TTL_S = 600  # dev-stub only; the Supabase Auth path uses its own OTP expiry


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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
                "device_id": report.get("device_id"),
            }).raise_for_status()
            batch = report.get("indicator_batch") or []
            if batch:
                self._client.post(f"{self._rest}/rpc/ingest_indicators",
                                  json={"batch": batch}).raise_for_status()
                log.info("report ingested %d indicators", len(batch))
        except Exception as exc:
            log.warning("report persist failed: %s", exc)


# ---------------------------------------------------------------------------
# UC-13 Manage Profile & Notifications (FR-14/15/16)
#
# device_id is a hub, not a chain: a profile is optional and is linked to
# the device rather than owning its scan/report history, so deleting a
# profile never deletes that history. Mirrors the ThreatIntelClient /
# SupabaseThreatIntelClient stub-vs-live split above.
# ---------------------------------------------------------------------------

class ProfileStore:
    """Fallback stub used when Supabase env vars are absent (offline dev)."""

    def __init__(self):
        self._by_device: dict[str, dict] = {}
        self._otp: dict[str, tuple[str, float]] = {}  # email -> (code_hash, expires_at)

    def upsert(self, device_id: str, display_name: Optional[str] = None,
               email: Optional[str] = None, total_scans: Optional[int] = None,
               total_reports: Optional[int] = None) -> dict:
        profile = self._by_device.get(device_id)
        if profile is None:
            profile = {
                "device_id": device_id,
                "display_name": display_name,
                "email": email,
                "notification_prefs": dict(DEFAULT_NOTIFICATION_PREFS),
                "total_scans": total_scans or 0,
                "total_reports": total_reports or 0,
            }
            self._by_device[device_id] = profile
        else:
            if display_name is not None:
                profile["display_name"] = display_name
            if email is not None:
                profile["email"] = email
        return profile

    def get(self, device_id: str) -> Optional[dict]:
        return self._by_device.get(device_id)

    def update_notification_prefs(self, device_id: str, prefs: dict) -> Optional[dict]:
        profile = self._by_device.get(device_id)
        if profile is None:
            return None
        profile["notification_prefs"] = prefs
        return profile

    def increment_reports(self, device_id: str) -> None:
        profile = self._by_device.get(device_id)
        if profile:
            profile["total_reports"] += 1

    def request_recovery(self, email: str) -> None:
        code = f"{secrets.randbelow(1_000_000):06d}"
        self._otp[email] = (hash_indicator(code), time.time() + RECOVERY_CODE_TTL_S)
        log.info("DEV recovery code for %s: %s (stub only — never returned by the API)",
                  email, code)

    def verify_recovery(self, email: str, code: str, new_device_id: str) -> Optional[dict]:
        entry = self._otp.get(email)
        if not entry or time.time() > entry[1] or hash_indicator(code) != entry[0]:
            return None
        del self._otp[email]
        profile = next((p for p in self._by_device.values() if p.get("email") == email), None)
        if profile is None:
            return None
        del self._by_device[profile["device_id"]]
        profile["device_id"] = new_device_id
        self._by_device[new_device_id] = profile
        return profile


class SupabaseProfileStore(ProfileStore):
    """Live client for user_profiles. Recovery rides Supabase Auth's own
    email-OTP flow (POST /auth/v1/otp then /auth/v1/verify) rather than a
    hand-rolled code store, so no separate email-sending integration is
    needed — the project's existing Supabase instance already has one.
    """

    def __init__(self, base_url: str, key: str):
        import httpx
        self._rest = f"{base_url.rstrip('/')}/rest/v1"
        self._auth = f"{base_url.rstrip('/')}/auth/v1"
        self._client = httpx.Client(
            headers={"apikey": key, "Authorization": f"Bearer {key}"},
            timeout=3.0,
        )

    def upsert(self, device_id, display_name=None, email=None,
               total_scans=None, total_reports=None):
        body = {"device_id": device_id}
        if display_name is not None:
            body["display_name"] = display_name
        if email is not None:
            body["email"] = email
        if total_scans is not None:
            body["total_scans"] = total_scans
        if total_reports is not None:
            body["total_reports"] = total_reports
        try:
            r = self._client.post(
                f"{self._rest}/user_profiles",
                params={"on_conflict": "device_id"},
                headers={"Prefer": "resolution=merge-duplicates,return=representation"},
                json=body,
            )
            r.raise_for_status()
            rows = r.json()
            return rows[0] if rows else None
        except Exception as exc:
            log.warning("profile upsert failed: %s", exc)
            return None

    def get(self, device_id):
        try:
            r = self._client.get(
                f"{self._rest}/user_profiles",
                params={"device_id": f"eq.{device_id}", "select": "*", "limit": "1"},
            )
            r.raise_for_status()
            rows = r.json()
            return rows[0] if rows else None
        except Exception as exc:
            log.warning("profile lookup failed: %s", exc)
            return None

    def update_notification_prefs(self, device_id, prefs):
        try:
            r = self._client.patch(
                f"{self._rest}/user_profiles",
                params={"device_id": f"eq.{device_id}"},
                headers={"Prefer": "return=representation"},
                json={"notification_prefs": prefs, "last_active": _now_iso()},
            )
            r.raise_for_status()
            rows = r.json()
            return rows[0] if rows else None
        except Exception as exc:
            log.warning("notification prefs update failed: %s", exc)
            return None

    def increment_reports(self, device_id):
        try:
            self._client.post(f"{self._rest}/rpc/increment_profile_reports",
                              json={"p_device_id": device_id}).raise_for_status()
        except Exception as exc:
            log.warning("increment_profile_reports failed: %s", exc)

    def request_recovery(self, email):
        try:
            self._client.post(f"{self._auth}/otp",
                              json={"email": email, "create_user": True}).raise_for_status()
        except Exception as exc:
            log.warning("recovery OTP request failed: %s", exc)

    def verify_recovery(self, email, code, new_device_id):
        try:
            r = self._client.post(f"{self._auth}/verify",
                                  json={"type": "email", "email": email, "token": code})
            if r.status_code != 200:
                return None
        except Exception as exc:
            log.warning("recovery OTP verify failed: %s", exc)
            return None
        try:
            r = self._client.patch(
                f"{self._rest}/user_profiles",
                params={"email": f"eq.{email}"},
                headers={"Prefer": "return=representation"},
                json={"device_id": new_device_id, "last_active": _now_iso()},
            )
            r.raise_for_status()
            rows = r.json()
            return rows[0] if rows else None
        except Exception as exc:
            log.warning("profile relink failed: %s", exc)
            return None


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
    device_id: Optional[str] = Field(None, max_length=100)


class ProfileRequest(BaseModel):
    device_id: str = Field(..., min_length=1, max_length=100)
    display_name: Optional[str] = Field(None, max_length=60)
    email: Optional[str] = Field(None, max_length=254)
    total_scans: Optional[int] = Field(None, ge=0)
    total_reports: Optional[int] = Field(None, ge=0)


class NotificationPrefsRequest(BaseModel):
    device_id: str = Field(..., min_length=1, max_length=100)
    alert_threshold: str = Field(
        ..., pattern="^(SAFE|LOW_RISK|MEDIUM_RISK|HIGH_RISK|CRITICAL)$")
    retroactive_updates: bool = True
    report_outcomes: bool = True
    digest_frequency: str = Field(..., pattern="^(off|daily|weekly)$")


class RecoveryRequest(BaseModel):
    email: str = Field(..., max_length=254)


class RecoveryVerifyRequest(BaseModel):
    email: str = Field(..., max_length=254)
    code: str = Field(..., min_length=6, max_length=6)
    device_id: str = Field(..., min_length=1, max_length=100)


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
    profiles = SupabaseProfileStore(_supabase_url, _supabase_key)
    log.info("Threat intel: Supabase client active (%s)", _supabase_url)
else:
    intel = ThreatIntelClient()
    profiles = ProfileStore()
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
        "device_id": req.device_id,
        "received_at": time.time(),
    }

    # OBJ-03 / FR-07: confirmed-scam reports become shared indicators so
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
    if req.device_id:
        profiles.increment_reports(req.device_id)  # no-op if no profile exists
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


# ---------------------------------------------------------------------------
# UC-13 Manage Profile & Notifications (FR-14/15/16)
# ---------------------------------------------------------------------------

@app.post("/api/v1/profile", dependencies=[Depends(require_api_key)])
def create_or_update_profile(req: ProfileRequest):
    profile = profiles.upsert(
        device_id=req.device_id,
        display_name=req.display_name,
        email=req.email,
        total_scans=req.total_scans,
        total_reports=req.total_reports,
    )
    if profile is None:
        raise HTTPException(status_code=503, detail="Profile service unavailable")
    return profile


@app.get("/api/v1/profile/{device_id}", dependencies=[Depends(require_api_key)])
def get_profile(device_id: str):
    profile = profiles.get(device_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="No profile for this device")
    return profile


@app.patch("/api/v1/profile/notifications", dependencies=[Depends(require_api_key)])
def update_notifications(req: NotificationPrefsRequest):
    prefs = {
        "alert_threshold": req.alert_threshold,
        "retroactive_updates": req.retroactive_updates,
        "report_outcomes": req.report_outcomes,
        "digest_frequency": req.digest_frequency,
    }
    profile = profiles.update_notification_prefs(req.device_id, prefs)
    if profile is None:
        raise HTTPException(status_code=404, detail="No profile for this device")
    return profile


@app.post("/api/v1/profile/recovery/request", dependencies=[Depends(require_api_key)])
def request_recovery(req: RecoveryRequest):
    # Always 202, whether or not the email has a profile — never reveal
    # which emails are registered.
    profiles.request_recovery(req.email)
    return {"status": "code_sent"}


@app.post("/api/v1/profile/recovery/verify", dependencies=[Depends(require_api_key)])
def verify_recovery(req: RecoveryVerifyRequest):
    profile = profiles.verify_recovery(req.email, req.code, req.device_id)
    if profile is None:
        raise HTTPException(status_code=400, detail="Invalid or expired code")
    return profile
