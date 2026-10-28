"""Tests for the A4 post-model rule layer: link extraction and brand rules."""

import json
import os
import sys

import pytest

ML_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ML_DIR)

from features import (  # noqa: E402
    canonical_url, extract_links, extract_rules, is_protected_domain,
)

BASELINE_PATH = os.path.join(ML_DIR, "tests", "fixtures", "legit_baseline.json")


@pytest.fixture(scope="module")
def scorer():
    from score import ScamScorer
    return ScamScorer(os.path.join(ML_DIR, "model.joblib"))


# --- Fix A: scheme-less links are extracted and canonicalised -------------

@pytest.mark.parametrize("text, expected", [
    ("SARS refund of R3,450 approved. Claim now: bit.ly/sars-rf",
     "http://bit.ly/sars-rf"),
    ("Verify at fnb-verify.co.za/login now", "http://fnb-verify.co.za/login"),
    ("Go to www.sassa-grant.online today", "http://www.sassa-grant.online"),
    ("Visit https://www.sars.gov.za for status.", "https://www.sars.gov.za"),
    ("Check sars-refund.xyz", "http://sars-refund.xyz"),
])
def test_links_are_extracted_and_canonicalised(text, expected):
    assert extract_rules(text).urls == [expected]


@pytest.mark.parametrize("text", [
    "Pay R3.50 now",
    "e.g. this",
    "Meet at 12.30pm",
    "Email name@fnb.co.za please",
    "Hello.How are you",       # run-together sentence, not a link
    "Capitec: R250.00 paid to Checkers. Avail bal R1,204.33",
])
def test_non_links_are_not_extracted(text):
    assert extract_rules(text).urls == []


def test_trailing_punctuation_stripped_and_duplicates_merged():
    text = "Claim (bit.ly/a), then http://bit.ly/a or bit.ly/a."
    assert extract_links(text) == ["bit.ly/a", "http://bit.ly/a"]
    assert extract_rules(text).urls == ["http://bit.ly/a"]


def test_canonical_url_only_strips_and_adds_scheme():
    assert canonical_url("bit.ly/SARS-rf!") == "http://bit.ly/SARS-rf"
    assert canonical_url("HTTPS://Evil.com/X") == "HTTPS://Evil.com/X"


# --- Fix A2: shortener / official brand domains are protected -------------

@pytest.mark.parametrize("host, protected", [
    ("bit.ly", True), ("www.bit.ly", True), ("tinyurl.com", True),
    ("fnb.co.za", True), ("www.fnb.co.za", True),
    ("secure.sarsefiling.co.za", True), ("gotyme.co.za", True),
    ("fnb-verify.co.za", False), ("notfnb.co.za", False), ("evil.com", False),
])
def test_protected_domains(host, protected):
    assert is_protected_domain(host) is protected


# --- False-positive guard: legitimate messages are unchanged --------------

def _baseline():
    with open(BASELINE_PATH) as f:
        return json.load(f)["messages"]


@pytest.mark.parametrize("name", list(_baseline()))
def test_legitimate_messages_score_exactly_as_before(scorer, name):
    case = _baseline()[name]
    assert scorer.score(case["text"]) == case["expected"]
