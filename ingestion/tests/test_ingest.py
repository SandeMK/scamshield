"""Offline tests for ingestion normalization and parsing."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ingest import hash_indicator, domain_of, indicator_rows


def test_hash_is_normalized_sha256():
    assert hash_indicator("HTTP://Evil.COM/x ") == hash_indicator("http://evil.com/x")
    assert len(hash_indicator("x")) == 64


def test_domain_extraction():
    assert domain_of("http://evil.com:8080/path?q=1") == "evil.com"
    assert domain_of("evil.co.za/login") == "evil.co.za"


def test_indicator_rows_url_and_domain():
    rows = list(indicator_rows("http://evil.com/x", "urlhaus", "malware", 90))
    assert [r["indicator_type"] for r in rows] == ["url", "domain"]
    assert rows[0]["reputation"] == 90 and rows[1]["reputation"] == 70


def test_hash_matches_api_module():
    """Ingestion and API must produce identical hashes for the same value."""
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__)))), "api"))
    from main import hash_indicator as api_hash
    assert api_hash("http://evil.com/x") == hash_indicator("http://evil.com/x")


# --- URLhaus API (Auth-Key) -------------------------------------------------

import pytest  # noqa: E402

import ingest  # noqa: E402

URLHAUS_SAMPLE = {
    "query_status": "ok",
    "urls": [
        {"url": "http://evil.com/x.exe", "threat": "malware_download",
         "url_status": "online", "host": "evil.com"},
        {"url": "http://1.2.3.4:8080/bins/a", "threat": None, "host": "1.2.3.4"},
        {"url": "", "threat": "malware_download"},
    ],
}


def test_urlhaus_rows_from_api_payload():
    rows = ingest.urlhaus_rows(URLHAUS_SAMPLE)
    assert [(r["indicator_type"], r["threat_tag"]) for r in rows] == [
        ("url", "malware_download"), ("domain", "malware_download"),
        ("url", "malware"), ("domain", "malware"),
    ]
    assert rows[0]["indicator_hash"] == hash_indicator("http://evil.com/x.exe")
    assert rows[3]["indicator_hash"] == hash_indicator("1.2.3.4")


def test_urlhaus_no_results_and_errors():
    assert ingest.urlhaus_rows({"query_status": "no_results"}) == []
    with pytest.raises(RuntimeError):
        ingest.urlhaus_rows({"query_status": "unknown_auth_key"})


def test_fetch_urlhaus_needs_key_and_sends_it_as_header(monkeypatch):
    monkeypatch.delenv("URLHAUS_AUTH_KEY", raising=False)
    with pytest.raises(RuntimeError, match="URLHAUS_AUTH_KEY"):
        ingest.fetch_urlhaus()

    seen = {}

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return URLHAUS_SAMPLE

    def fake_get(url, headers=None, timeout=None):
        seen.update(url=url, headers=headers)
        return FakeResponse()

    monkeypatch.setenv("URLHAUS_AUTH_KEY", "test-key")
    monkeypatch.setattr(ingest.requests, "get", fake_get)
    assert len(ingest.fetch_urlhaus()) == 4
    assert seen["headers"] == {"Auth-Key": "test-key"}
    assert "test-key" not in seen["url"]
