"""Threat-intel lookup through the live Supabase client against a fake
PostgREST (httpx.MockTransport) — A4 Fix A / A2, brief §4.5."""

import json
import os
import sys

import httpx
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient  # noqa: E402
import main  # noqa: E402
from main import SupabaseThreatIntelClient, hash_indicator  # noqa: E402

client = TestClient(main.app)
KEY = {"X-API-Key": "demo-key"}


class FakePostgrest:
    """Just enough of /rest/v1 for record_report() and lookup()."""

    def __init__(self):
        self.rows = []
        self.reports = []
        self.lookups = 0
        self.failing = set()   # path suffixes that answer 500

    def __call__(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if any(path.endswith(f) for f in self.failing):
            return httpx.Response(500)
        if path.endswith("/rpc/ingest_indicators"):
            self.rows.extend(json.loads(request.content)["batch"])
            return httpx.Response(200, json=None)
        if path.endswith("/reports"):
            self.reports.append(json.loads(request.content))
            return httpx.Response(201)
        if path.endswith("/indicators"):
            self.lookups += 1
            params = request.url.params
            wanted = set(params["indicator_hash"][len("in.("):-1].split(","))
            kind = params["indicator_type"][len("eq."):]
            hits = [r for r in self.rows
                    if r["indicator_hash"] in wanted and r["indicator_type"] == kind]
            return httpx.Response(200, json=hits[:1])
        return httpx.Response(404)


@pytest.fixture
def db(monkeypatch):
    fake = FakePostgrest()
    live = SupabaseThreatIntelClient("https://db.test", "test-key",
                                     transport=httpx.MockTransport(fake))
    monkeypatch.setattr(main, "intel", live)
    return fake


def _score(text):
    r = client.post("/api/v1/score/sms", json={"text": text}, headers=KEY)
    assert r.status_code == 200
    return r.json()


def _report(text):
    r = client.post("/api/v1/report", json={"text": text, "report_type": "scam"},
                    headers=KEY)
    assert r.status_code == 200


def test_reported_bare_shortener_link_matches_later_scans(db):
    _report("Your parcel is waiting, pay the fee at bit.ly/xyz")

    for later in ("Last chance to pay: bit.ly/xyz", "Pay now at http://bit.ly/xyz",
                  "Pay now at https://bit.ly/xyz"):
        body = _score(later)
        assert body["explanation_codes"][0]["code"] == "INTEL_MATCH"
        assert body["risk_score"] >= 90


def test_reported_sars_lure_shows_intel_and_brand_codes(db):
    sars = "SARS refund of R3,450 approved. Claim now: bit.ly/sars-rf"
    _report(sars)
    codes = [c["code"] for c in _score(sars)["explanation_codes"]]
    assert codes[0] == "INTEL_MATCH"
    assert "BRAND_LINK_MISMATCH" in codes


def test_sars_codes_after_report_stay_within_limit_with_one_ml_code(db):
    sars = "SARS refund of R3,450 approved. Claim now: bit.ly/sars-rf"
    _report(sars)
    codes = [c["code"] for c in _score(sars)["explanation_codes"]]
    # 8 candidates (INTEL_MATCH + 6 rule codes + ML) are capped once, at the end
    assert codes == ["INTEL_MATCH", "BRAND_LINK_MISMATCH", "URL_SHORTENER",
                     "URGENCY_LANGUAGE", "IMPERSONATION", "ML_PHISHING_PATTERN"]
    assert 3 <= len(codes) <= 6
    assert sum(c.startswith("ML_") for c in codes) == 1     # ET-03


@pytest.mark.parametrize("failing, still_written", [
    ("/reports", "rows"),                     # report row down, batch still lands
    ("/rpc/ingest_indicators", "reports"),    # batch down, report row still lands
])
def test_report_returns_503_when_either_write_fails(db, failing, still_written):
    db.failing.add(failing)
    r = client.post("/api/v1/report",
                    json={"text": "Pay the fee at bit.ly/xyz", "report_type": "scam"},
                    headers=KEY)
    assert r.status_code == 503
    assert r.json()["detail"] == "Report not saved"
    assert getattr(db, still_written)          # the other write was not skipped


def test_bare_link_matches_feed_url_stored_with_https(db):
    db.rows.append({"indicator_hash": hash_indicator("https://evil-pay.com/login"),
                    "indicator_type": "url", "source": "openphish"})
    body = _score("Account locked. Unlock at evil-pay.com/login")
    assert body["explanation_codes"][0]["code"] == "INTEL_MATCH"
    assert "openphish" in body["explanation_codes"][0]["detail"]


def test_scheme_variants():
    from main import scheme_variants
    assert scheme_variants("bit.ly/x") == ["http://bit.ly/x", "https://bit.ly/x"]
    assert scheme_variants("HTTPS://bit.ly/x") == ["http://bit.ly/x", "https://bit.ly/x"]
    assert scheme_variants("ftp://evil.com/x") == ["ftp://evil.com/x"]


def test_report_never_stores_shortener_or_brand_domain(db):
    _report("Pay at bit.ly/xyz or fnb.co.za/xyz, or evil-pay.com/xyz")

    domains = {r["indicator_hash"] for r in db.rows if r["indicator_type"] == "domain"}
    assert hash_indicator("bit.ly") not in domains
    assert hash_indicator("fnb.co.za") not in domains
    assert hash_indicator("evil-pay.com") in domains        # ordinary domains still stored
    urls = {r["indicator_hash"] for r in db.rows if r["indicator_type"] == "url"}
    assert hash_indicator("http://bit.ly/xyz") in urls       # URL-level kept


def test_shortener_domain_is_never_matched(db):
    db.rows.append({"indicator_hash": hash_indicator("bit.ly"),  # e.g. from an old feed row
                    "indicator_type": "domain", "source": "feed"})
    body = _score("See bit.ly/unrelated-link")
    assert "INTEL_MATCH" not in {c["code"] for c in body["explanation_codes"]}


def test_lookup_budget_is_three_urls_and_two_queries_each(db):
    _score("a.com/1 b.com/2 c.com/3 d.com/4 e.com/5")
    assert db.lookups == 3 * 2
