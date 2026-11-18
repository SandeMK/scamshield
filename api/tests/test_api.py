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


def test_profile_email_taken_by_another_device_is_409():
    r = client.post("/api/v1/profile",
                    json={"device_id": "dev-email-a", "email": "taken@example.com"},
                    headers=KEY)
    assert r.status_code == 200
    # Same device re-saving its own email is fine.
    r = client.post("/api/v1/profile",
                    json={"device_id": "dev-email-a", "email": "taken@example.com"},
                    headers=KEY)
    assert r.status_code == 200
    r = client.post("/api/v1/profile",
                    json={"device_id": "dev-email-b", "email": "taken@example.com"},
                    headers=KEY)
    assert r.status_code == 409
    assert "already linked" in r.json()["detail"]
    assert client.get("/api/v1/profile/dev-email-b", headers=KEY).status_code == 404


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
    }, headers=KEY)
    assert r.status_code == 200
    assert r.json()["notification_prefs"] == {
        "alert_threshold": "HIGH_RISK", "retroactive_updates": False}


def test_notification_prefs_ignores_removed_fields_from_old_clients():
    # Builds released before FR-15 was trimmed still send these two fields.
    client.post("/api/v1/profile", json={"device_id": "dev-4b"}, headers=KEY)
    r = client.patch("/api/v1/profile/notifications", json={
        "device_id": "dev-4b",
        "alert_threshold": "CRITICAL",
        "retroactive_updates": True,
        "report_outcomes": False,
        "digest_frequency": "weekly",
    }, headers=KEY)
    assert r.status_code == 200
    assert r.json()["notification_prefs"] == {
        "alert_threshold": "CRITICAL", "retroactive_updates": True}


def test_notification_prefs_requires_existing_profile():
    r = client.patch("/api/v1/profile/notifications", json={
        "device_id": "never-created",
        "alert_threshold": "SAFE",
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


# --- FR-16 recovery: a valid code must never be reported as "invalid" ------

import httpx  # noqa: E402
import pytest  # noqa: E402

import main  # noqa: E402


def _recover(monkeypatch, email, device_id, code="123456"):
    """Request a recovery code (pinned via randbelow), then verify it."""
    monkeypatch.setattr(main.secrets, "randbelow", lambda _n: int(code))
    client.post("/api/v1/profile/recovery/request", json={"email": email}, headers=KEY)
    return client.post("/api/v1/profile/recovery/verify", json={
        "email": email, "code": code, "device_id": device_id,
    }, headers=KEY)


def test_recovery_verify_moves_profile_to_new_device(monkeypatch):
    client.post("/api/v1/profile", json={"device_id": "dev-7", "email": "zanele@example.com"},
                headers=KEY)
    r = _recover(monkeypatch, "zanele@example.com", "dev-7-new")
    assert r.status_code == 200
    assert r.json()["device_id"] == "dev-7-new"
    assert client.get("/api/v1/profile/dev-7", headers=KEY).status_code == 404


def test_recovery_verify_valid_code_but_no_profile_is_404(monkeypatch):
    r = _recover(monkeypatch, "nobody@example.com", "dev-8")
    assert r.status_code == 404
    assert "Invalid" not in r.json()["detail"]


def test_recovery_verify_onto_device_with_own_profile_is_409(monkeypatch):
    client.post("/api/v1/profile", json={"device_id": "dev-9", "email": "sipho@example.com"},
                headers=KEY)
    client.post("/api/v1/profile", json={"device_id": "dev-10", "email": "lindi@example.com"},
                headers=KEY)
    r = _recover(monkeypatch, "sipho@example.com", "dev-10")
    assert r.status_code == 409
    assert "Invalid" not in r.json()["detail"]
    # Neither profile moved.
    assert client.get("/api/v1/profile/dev-9", headers=KEY).json()["email"] == "sipho@example.com"
    assert client.get("/api/v1/profile/dev-10", headers=KEY).json()["email"] == "lindi@example.com"


def _live_store(patch_response):
    """SupabaseProfileStore whose Auth verify succeeds and whose
    user_profiles PATCH returns patch_response."""
    def fake(request):
        if request.url.path.endswith("/auth/v1/verify"):
            return httpx.Response(200, json={})
        return patch_response
    return main.SupabaseProfileStore("https://db.example", "k",
                                     transport=httpx.MockTransport(fake))


@pytest.mark.parametrize("response, status", [
    (httpx.Response(409, json={
        "code": "23505",
        "details": "Key (device_id)=(dev-x) already exists.",
        "message": "duplicate key value violates unique constraint "
                   "\"user_profiles_device_id_key\""}), 409),
    (httpx.Response(200, json=[]), 404),
    (httpx.Response(500, json={"message": "boom"}), 503),
])
def test_live_relink_failures_map_to_their_own_status(response, status):
    with pytest.raises(main.RecoveryRelinkError) as exc:
        _live_store(response).verify_recovery("a@example.com", "123456", "dev-x")
    assert exc.value.status_code == status


def test_live_wrong_code_still_returns_none():
    def fake(request):
        return httpx.Response(403, json={"msg": "Token has expired or is invalid"})
    store = main.SupabaseProfileStore("https://db.example", "k",
                                      transport=httpx.MockTransport(fake))
    assert store.verify_recovery("a@example.com", "000000", "dev-x") is None
