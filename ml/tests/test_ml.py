"""Tests for the ScamShield rule engine and hybrid scorer."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from features import extract_rules, rule_feature_vector, FEATURE_ORDER


SCAM = ("URGENT: Your FNB account has been suspended. "
        "Verify now at http://bit.ly/fnb-secure or lose access.")
HAM = "Hey, are we still on for lunch tomorrow at 1?"


def test_feature_vector_length_matches_order():
    assert len(rule_feature_vector(SCAM)) == len(FEATURE_ORDER)


def test_scam_message_fires_expected_rules():
    r = extract_rules(SCAM)
    codes = {x["code"] for x in r.reasons}
    assert {"URL_PRESENT", "URL_SHORTENER", "URGENCY_LANGUAGE",
            "IMPERSONATION", "CREDENTIAL_REQUEST"} <= codes
    assert r.rule_score >= 50


def test_benign_message_fires_few_rules():
    r = extract_rules(HAM)
    assert r.rule_score <= 20
    assert not r.urls


def test_url_extraction():
    r = extract_rules("Claim at www.vcm-prize.xyz now")
    assert r.urls


def test_scorer_contract():
    """Scorer must return score 0-100, a label, and >= 3 reason codes."""
    model_path = os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "model.joblib")
    if not os.path.exists(model_path):
        import pytest
        pytest.skip("model.joblib not trained yet")
    from score import ScamScorer
    scorer = ScamScorer(model_path)
    for text in (SCAM, HAM):
        res = scorer.score(text)
        assert 0 <= res["risk_score"] <= 100
        assert res["classification"] in {"SAFE", "LOW_RISK", "MEDIUM_RISK",
                                         "HIGH_RISK", "CRITICAL"}
        assert len(res["explanation_codes"]) >= 3
    assert scorer.score(SCAM)["risk_score"] > scorer.score(HAM)["risk_score"]
