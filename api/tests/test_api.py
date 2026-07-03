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
