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
        self.lookups = 0

    def __call__(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/rpc/ingest_indicators"):
            self.rows.extend(json.loads(request.content)["batch"])
            return httpx.Response(200, json=None)
        if path.endswith("/reports"):
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
