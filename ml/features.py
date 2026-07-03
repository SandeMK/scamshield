"""
ScamShield rule-based feature extraction.

Each rule produces both a numeric feature (for the hybrid model) and a
human-readable reason code (for explainability). This is the single source
of truth used by training, scoring, and the cloud API.
"""

import re
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Rule definitions
# ---------------------------------------------------------------------------

URL_PATTERN = re.compile(r"(https?://\S+|www\.\S+|\b[a-z0-9-]+\.(?:com|net|org|co\.za|info|xyz|top|click|link|site|online)\b\S*)", re.I)
SHORTENER_PATTERN = re.compile(r"\b(bit\.ly|tinyurl\.com|goo\.gl|t\.co|is\.gd|ow\.ly|cutt\.ly|rb\.gy|shorturl\.at|tiny\.cc)\b", re.I)
PHONE_PATTERN = re.compile(r"(\+27\d{9}|\b0\d{9}\b|\b\d{5,6}\b)")  # SA numbers + premium shortcodes
CURRENCY_PATTERN = re.compile(r"(R\s?\d[\d,\.]*|ZAR|\$\s?\d[\d,\.]*|£\s?\d[\d,\.]*)", re.I)

URGENCY_WORDS = [
    "urgent", "immediately", "now", "act fast", "expires", "expire", "final notice",
    "last chance", "within 24", "asap", "suspended", "deactivated", "verify now",
]
IMPERSONATION_WORDS = [
    "sars", "fnb", "absa", "nedbank", "capitec", "standard bank", "tymebank",
    "post office", "courier", "delivery", "customs", "efiling", "e-filing",
    "account", "bank", "sassa", "nsfas", "vodacom", "mtn", "telkom",
]
PRIZE_WORDS = [
    "won", "winner", "prize", "claim", "reward", "congratulations", "congrats",
    "free", "voucher", "lottery", "lucky", "selected", "cash",
]
CREDENTIAL_WORDS = [
    "password", "pin", "otp", "one-time", "login", "log in", "verify", "confirm",
    "update your details", "id number", "card number", "cvv",
]

# Reason codes: (code, description, weight for rule score)
REASON_CODES = {
    "URL_PRESENT":        ("Message contains a link", 10),
    "URL_SHORTENER":      ("Link uses a URL-shortening service that hides the destination", 20),
    "URGENCY_LANGUAGE":   ("Uses urgent or pressuring language", 15),
    "IMPERSONATION":      ("References a bank, SARS, or other trusted institution", 15),
    "PRIZE_LURE":         ("Promises a prize, reward, or free offer", 15),
    "CREDENTIAL_REQUEST": ("Asks for credentials, PIN, OTP, or personal details", 20),
    "MONEY_MENTION":      ("Mentions money or a specific amount", 10),
    "SUSPICIOUS_NUMBER":  ("Contains a phone number or premium shortcode", 5),
    "ALL_CAPS_EMPHASIS":  ("Excessive capitalisation typical of scam messages", 5),
}

FEATURE_ORDER = list(REASON_CODES.keys())


@dataclass
class RuleResult:
    features: dict          # code -> 0/1
    reasons: list           # fired reason codes with descriptions
    rule_score: int         # 0-100 capped sum of fired weights
    urls: list              # extracted URLs


def _contains_any(text: str, words) -> bool:
    t = text.lower()
    return any(w in t for w in words)


def extract_rules(text: str) -> RuleResult:
    urls = URL_PATTERN.findall(text)
    caps_ratio = sum(1 for c in text if c.isupper()) / max(len(text), 1)

    fired = {
        "URL_PRESENT": bool(urls),
        "URL_SHORTENER": bool(SHORTENER_PATTERN.search(text)),
        "URGENCY_LANGUAGE": _contains_any(text, URGENCY_WORDS),
        "IMPERSONATION": _contains_any(text, IMPERSONATION_WORDS),
        "PRIZE_LURE": _contains_any(text, PRIZE_WORDS),
        "CREDENTIAL_REQUEST": _contains_any(text, CREDENTIAL_WORDS),
        "MONEY_MENTION": bool(CURRENCY_PATTERN.search(text)),
        "SUSPICIOUS_NUMBER": bool(PHONE_PATTERN.search(text)),
        "ALL_CAPS_EMPHASIS": caps_ratio > 0.3 and len(text) > 20,
    }

    features = {code: int(v) for code, v in fired.items()}
    reasons = [
        {"code": code, "description": REASON_CODES[code][0]}
        for code, v in fired.items() if v
    ]
    rule_score = min(100, sum(REASON_CODES[c][1] for c, v in fired.items() if v))

    return RuleResult(features=features, reasons=reasons, rule_score=rule_score, urls=urls)


def rule_feature_vector(text: str):
    """Numeric vector in FEATURE_ORDER, for stacking with TF-IDF."""
    f = extract_rules(text).features
    return [f[c] for c in FEATURE_ORDER]


# ---------------------------------------------------------------------------
# Engineered features (Assignment 2, ET-03): URL length, special character
# count, IP-based URL flag, keyword frequency scores, message structure.
# ---------------------------------------------------------------------------

IP_URL_PATTERN = re.compile(r"https?://\d{1,3}(?:\.\d{1,3}){3}", re.I)
HIGH_RISK_KEYWORDS = ["verify", "refund", "suspended", "urgent", "claim",
                      "confirm", "account", "prize", "winner", "expires"]

ENGINEERED_ORDER = [
    "msg_length", "url_count", "max_url_length", "special_char_ratio",
    "ip_url_flag", "url_path_segments", "keyword_frequency",
]


def engineered_features(text: str):
    urls = URL_PATTERN.findall(text)
    max_url = max(urls, key=len) if urls else ""
    specials = sum(1 for c in text if not c.isalnum() and not c.isspace())
    tokens = max(len(text.split()), 1)
    kw_hits = sum(text.lower().count(k) for k in HIGH_RISK_KEYWORDS)
    return [
        min(len(text) / 160.0, 4.0),                 # msg_length (SMS units)
        float(len(urls)),                            # url_count
        min(len(max_url) / 50.0, 4.0),               # max_url_length (norm)
        specials / max(len(text), 1),                # special_char_ratio
        float(bool(IP_URL_PATTERN.search(text))),    # ip_url_flag
        float(max_url.count("/") - 2 if "://" in max_url else max_url.count("/")),
        kw_hits / tokens,                            # keyword_frequency
    ]


def full_feature_vector(text: str):
    """Rule flags + engineered features — the non-text half of the model input."""
    return rule_feature_vector(text) + engineered_features(text)
