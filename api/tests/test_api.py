"""Integration tests for the ScamShield scoring API."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

SCAM = ("URGENT: Your FNB account has been suspended. "
        "Verify now at http://bit.ly/fnb-secure or lose access.")
HAM = "Hey, are we still on for lunch tomorrow at 1?"


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["model_loaded"] is True


def test_score_sms_contract():
    r = client.post("/score/sms", json={"text": SCAM})
    assert r.status_code == 200
    body = r.json()
    assert 0 <= body["risk_score"] <= 100
    assert len(body["reasons"]) >= 3
    assert body["latency_ms"] < 2000  # success criterion: < 2 s


def test_scam_scores_higher_than_ham():
    scam = client.post("/score/sms", json={"text": SCAM}).json()
    ham = client.post("/score/sms", json={"text": HAM}).json()
    assert scam["risk_score"] > ham["risk_score"]
    assert scam["label"] == "HIGH_RISK"


def test_score_url():
    r = client.post("/score/url", json={"url": "http://bit.ly/fnb-secure"})
    assert r.status_code == 200
    body = r.json()
    assert body["indicator_hash"]
    assert len(body["indicator_hash"]) == 64  # sha256 hex


def test_report_hashes_pii():
    r = client.post("/report", json={"text": SCAM, "report_type": "scam"})
    assert r.status_code == 200
    body = r.json()["report"]
    assert body["text_hash"] and SCAM not in str(body)


def test_validation_rejects_empty():
    assert client.post("/score/sms", json={"text": ""}).status_code == 422


def test_stats():
    r = client.get("/stats")
    assert r.status_code == 200
    assert r.json()["requests_total"] >= 1
