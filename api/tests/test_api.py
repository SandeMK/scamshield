"""Integration tests for the ScamShield scoring API (Assignment 2 contract)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)
KEY = {"X-API-Key": "demo-key"}

SCAM = ("URGENT: Your FNB account has been suspended. "
        "Verify now at http://bit.ly/fnb-secure or lose access.")
HAM = "Hey, are we still on for lunch tomorrow at 1?"


def test_health_is_public_and_reports_model_version():
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert "model_version" in r.json()


def test_auth_enforced():
    assert client.post("/api/v1/score/sms", json={"text": SCAM}).status_code == 401
    bad = client.post("/api/v1/score/sms", json={"text": SCAM},
                      headers={"X-API-Key": "wrong"})
    assert bad.status_code == 401


def test_score_sms_contract():
    r = client.post("/api/v1/score/sms", json={"text": SCAM}, headers=KEY)
    assert r.status_code == 200
    body = r.json()
    assert 0 <= body["risk_score"] <= 100
    assert body["classification"] in {"SAFE", "LOW_RISK", "MEDIUM_RISK",
                                      "HIGH_RISK", "CRITICAL"}
    assert len(body["explanation_codes"]) >= 3
    assert {"code", "detail"} <= set(body["explanation_codes"][0])
    assert 0.0 <= body["ml_confidence"] <= 1.0
    assert 0 <= body["rule_sub_score"] <= 100
    assert body["model_version"]
    assert body["latency_ms"] < 2000


def test_scam_scores_higher_than_ham():
    scam = client.post("/api/v1/score/sms", json={"text": SCAM}, headers=KEY).json()
    ham = client.post("/api/v1/score/sms", json={"text": HAM}, headers=KEY).json()
    assert scam["risk_score"] > ham["risk_score"]
    assert scam["classification"] in ("HIGH_RISK", "CRITICAL")
    assert ham["classification"] in ("SAFE", "LOW_RISK")


def test_score_url():
    r = client.post("/api/v1/score/url",
                    json={"url": "http://bit.ly/fnb-secure"}, headers=KEY)
    assert r.status_code == 200
    assert len(r.json()["indicator_hash"]) == 64


def test_report_hashes_pii():
    r = client.post("/api/v1/report",
                    json={"text": SCAM, "report_type": "scam"}, headers=KEY)
    assert r.status_code == 200
    body = r.json()["report"]
    assert body["text_hash"] and SCAM not in str(body)


def test_intel_ingest_requires_admin_key():
    assert client.post("/api/v1/intel/ingest", headers=KEY).status_code == 401


def test_analytics_summary():
    r = client.get("/api/v1/analytics/summary", headers=KEY)
    assert r.status_code == 200
    assert r.json()["requests_total"] >= 1


# --- UC-13 Manage Profile & Notifications (FR-14/15/16) --------------------

def test_profile_requires_api_key():
    assert client.post("/api/v1/profile", json={"device_id": "dev-1"}).status_code == 401


def test_profile_create_and_fetch():
    r = client.post("/api/v1/profile",
                    json={"device_id": "dev-1", "display_name": "Thabo"},
                    headers=KEY)
    assert r.status_code == 200
    assert r.json()["display_name"] == "Thabo"

    r = client.get("/api/v1/profile/dev-1", headers=KEY)
    assert r.status_code == 200
    assert r.json()["device_id"] == "dev-1"


def test_profile_not_found():
    assert client.get("/api/v1/profile/never-created", headers=KEY).status_code == 404


def test_profile_inherits_totals_on_creation():
    r = client.post("/api/v1/profile",
                    json={"device_id": "dev-2", "total_scans": 42, "total_reports": 3},
                    headers=KEY)
    body = r.json()
    assert body["total_scans"] == 42
    assert body["total_reports"] == 3


def test_report_increments_profile_total_reports():
    client.post("/api/v1/profile", json={"device_id": "dev-3"}, headers=KEY)
    client.post("/api/v1/report",
               json={"text": SCAM, "report_type": "scam", "device_id": "dev-3"},
               headers=KEY)
    profile = client.get("/api/v1/profile/dev-3", headers=KEY).json()
    assert profile["total_reports"] == 1


def test_notification_prefs_update_persists():
    client.post("/api/v1/profile", json={"device_id": "dev-4"}, headers=KEY)
    r = client.patch("/api/v1/profile/notifications", json={
        "device_id": "dev-4",
        "alert_threshold": "HIGH_RISK",
        "retroactive_updates": False,
        "report_outcomes": True,
        "digest_frequency": "weekly",
    }, headers=KEY)
    assert r.status_code == 200
    assert r.json()["notification_prefs"]["alert_threshold"] == "HIGH_RISK"


def test_notification_prefs_requires_existing_profile():
    r = client.patch("/api/v1/profile/notifications", json={
        "device_id": "never-created",
        "alert_threshold": "SAFE",
        "digest_frequency": "off",
    }, headers=KEY)
    assert r.status_code == 404


def test_recovery_request_never_reveals_whether_email_exists():
    r = client.post("/api/v1/profile/recovery/request",
                    json={"email": "unknown@example.com"}, headers=KEY)
    assert r.status_code == 200


def test_recovery_verify_rejects_wrong_code():
    client.post("/api/v1/profile", json={"device_id": "dev-5", "email": "thabo@example.com"},
               headers=KEY)
    client.post("/api/v1/profile/recovery/request", json={"email": "thabo@example.com"},
               headers=KEY)
    r = client.post("/api/v1/profile/recovery/verify", json={
        "email": "thabo@example.com", "code": "000000", "device_id": "dev-5-new",
    }, headers=KEY)
    assert r.status_code == 400
