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
