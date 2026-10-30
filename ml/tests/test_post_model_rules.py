"""Tests for the A4 post-model rule layer: link extraction and brand rules."""

import json
import os
import sys

import pytest

ML_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ML_DIR)

from features import (  # noqa: E402
    FEATURE_ORDER, brand_rule, canonical_url, extract_links, extract_rules,
    is_protected_domain,
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


# --- Fix B: SA brand impersonation via mismatched links -------------------

SARS_LURE = "SARS refund of R3,450 approved. Claim now: bit.ly/sars-rf"
FNB_LURE = ("FNB: Your account is on hold. Verify your details at "
            "fnb-secure-za.com/login within 24 hrs")


@pytest.mark.parametrize("text, code, detail", [
    (SARS_LURE, "BRAND_LINK_MISMATCH",
     "Mentions SARS but the link leads somewhere else"),
    (FNB_LURE, "BRAND_LOOKALIKE_DOMAIN",
     "Link imitates FNB but is not FNB's official website"),
])
def test_sa_lures_reach_high_risk_with_brand_code(scorer, text, code, detail):
    res = scorer.score(text)
    assert res["classification"] in ("HIGH_RISK", "CRITICAL")
    assert {"code": code, "detail": detail} in res["explanation_codes"]


def test_brand_code_survives_the_six_code_cap(scorer):
    codes = scorer.score(SARS_LURE)["explanation_codes"]   # 7 candidates
    assert len(codes) == 6
    assert codes[0]["code"] == "BRAND_LINK_MISMATCH"
    assert codes[-1]["code"] == "ML_PHISHING_PATTERN"     # ET-03: never capped away


def test_cap_keeps_exactly_one_ml_code_in_place():
    from score import cap_codes
    codes = [{"code": c} for c in
             ("INTEL_MATCH", "A", "B", "ML_PHISHING_PATTERN", "C", "D", "E", "F")]
    assert [c["code"] for c in cap_codes(codes)] == \
        ["INTEL_MATCH", "A", "B", "ML_PHISHING_PATTERN", "C", "D"]


@pytest.mark.parametrize("text, expected", [
    ("Your FNB OTP is 123456", None),                                # no link
    ("FNB: verify at fnb-verify.co.za/login",
     ("BRAND_LOOKALIKE_DOMAIN", "FNB")),                             # lookalike wins
    ("Absa: get the app at https://www.absa.co.za/app", None),       # official link
    ("SARS eFiling: https://secure.sarsefiling.co.za/landing", None),
    ("Capitec: see bit.ly/cap-help", ("BRAND_LINK_MISMATCH", "Capitec")),
    ("Win big at bit.ly/promo", None),                               # no brand
    ("Rewards at www.gotyme-rewards.top", ("BRAND_LOOKALIKE_DOMAIN", "TymeBank")),
    ("Pay at standard-bank-verify.com/x",
     ("BRAND_LOOKALIKE_DOMAIN", "Standard Bank")),
    ("Track it at sapo.pt/x", None),             # brand word only inside a link
])
def test_brand_rule(text, expected):
    assert brand_rule(text, extract_rules(text).urls) == expected


def test_only_one_brand_code_fires():
    reasons = extract_rules("FNB: verify at fnb-verify.co.za/login").reasons
    assert [r["code"] for r in reasons if r["code"].startswith("BRAND_")] == \
        ["BRAND_LOOKALIKE_DOMAIN"]


def test_brand_codes_are_not_model_features():
    assert list(extract_rules(FNB_LURE).features) == FEATURE_ORDER


def test_mobile_local_rules_use_the_same_lists():
    """mobile-app/lib/services/local_rules.dart ports BRANDS, the shortener
    list and the bare-link TLDs; they must not drift apart."""
    import re
    from features import BRANDS, URL_SHORTENERS, _BARE_LINK_TLDS
    dart_path = os.path.join(os.path.dirname(ML_DIR), "mobile-app", "lib",
                             "services", "local_rules.dart")
    if not os.path.exists(dart_path):
        pytest.skip("mobile-app not present")
    dart = open(dart_path).read()

    def strings(src):
        return tuple(re.findall(r"'([^']*)'", src))

    def const_list(name):
        return strings(re.search(rf"const {name} = \[(.*?)\];", dart, re.S).group(1))

    assert const_list("_urlShorteners") == URL_SHORTENERS
    assert const_list("_bareLinkTlds") == _BARE_LINK_TLDS
    entries = re.findall(r"_Brand\(\s*'([^']+)',\s*\[(.*?)\],\s*\[(.*?)\],\s*\[(.*?)\]\)",
                         dart, re.S)
    dart_brands = {name: {"text": strings(t), "host": strings(h), "domains": strings(d)}
                   for name, t, h, d in entries}
    assert dart_brands == BRANDS


# --- False-positive guard: legitimate messages are unchanged --------------

def _baseline():
    with open(BASELINE_PATH) as f:
        return json.load(f)["messages"]


@pytest.mark.parametrize("name", list(_baseline()))
def test_legitimate_messages_score_exactly_as_before(scorer, name):
    case = _baseline()[name]
    assert scorer.score(case["text"]) == case["expected"]
