"""
ScamShield rule-based feature extraction.

Each rule produces both a numeric feature (for the hybrid model) and a
human-readable reason code (for explainability). This is the single source
of truth used by training, scoring, and the cloud API.
"""

import re
from dataclasses import dataclass
from urllib.parse import urlparse

# ---------------------------------------------------------------------------
# Model-input rules — FROZEN.
# model.joblib was trained on exactly these patterns, word lists and
# FEATURE_ORDER. Changing any of them changes what the model sees and
# invalidates the reported F1 (tests/test_model_regression.py guards this).
# New detection belongs in a post-model rule layer that adds reason codes
# and rule score only, never model features.
# ---------------------------------------------------------------------------

MODEL_URL_PATTERN = re.compile(r"(https?://\S+|www\.\S+|\b[a-z0-9-]+\.(?:com|net|org|co\.za|info|xyz|top|click|link|site|online)\b\S*)", re.I)
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


# ---------------------------------------------------------------------------
# Post-model rule layer (A4). Supplies links for threat-intel lookup and
# the brand reason codes. Never feeds rule_feature_vector() or
# engineered_features(), so the trained model's inputs are unchanged.
# ---------------------------------------------------------------------------

URL_SHORTENERS = ("bit.ly", "t.co", "is.gd", "rb.gy", "cutt.ly", "tinyurl.com",
                  "ow.ly", "shorturl.at", "tiny.cc", "goo.gl")
# A bare "host.tld" with no path only counts as a link for familiar TLDs, so
# run-together sentences like "Hello.How are you" are not read as links.
_BARE_LINK_TLDS = ("com", "net", "org", "info", "biz", "xyz", "top", "click",
                   "link", "site", "online", "live", "shop", "app", "io", "za")
_LINK_HOST = r"(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+"
_LINK_CHAR = r"[^\s<>\"']"
_LINK_HOST_END = r"(?![\w-]|\.[a-z0-9])"   # host stops here; a sentence-ending "." is fine

LINK_PATTERN = re.compile(
    r"(?<![@\w.-])(?:"                      # not part of an email address or longer token
    r"https?://" + _LINK_CHAR + r"+"
    r"|www\." + _LINK_CHAR + r"+"
    r"|(?:" + "|".join(map(re.escape, URL_SHORTENERS)) + r")" + _LINK_HOST_END
    + r"(?:/" + _LINK_CHAR + r"*)?"
    r"|" + _LINK_HOST + r"[a-z]{2,24}/" + _LINK_CHAR + r"*"
    r"|" + _LINK_HOST + r"(?:" + "|".join(_BARE_LINK_TLDS) + r")" + _LINK_HOST_END
    + r")",
    re.I,
)
_SCHEME_PATTERN = re.compile(r"^[a-z][a-z0-9+.-]*://", re.I)
_TRAILING_PUNCT = ".,;:!?)\"'"

# Official domains verified 28 Oct 2026 (TymeBank rebranded to GoTyme Bank in
# Jan 2026; tymebank.co.za now redirects to gotyme.co.za).
# text: words that name the brand in a message; host: substrings that imitate
# it in a link's host; domains: the brand's own sites (subdomains included).
BRANDS = {
    "FNB": {"text": ("fnb", "first national bank"),
            "host": ("fnb", "firstnationalbank"),
            "domains": ("fnb.co.za",)},
    "Absa": {"text": ("absa",), "host": ("absa",),
             "domains": ("absa.co.za", "absa.africa")},
    "Standard Bank": {"text": ("standard bank", "standardbank"),
                      "host": ("standardbank",),
                      "domains": ("standardbank.co.za", "standardbank.com")},
    "Capitec": {"text": ("capitec",), "host": ("capitec",),
                "domains": ("capitecbank.co.za", "capitec.co.za")},
    "Nedbank": {"text": ("nedbank",), "host": ("nedbank",),
                "domains": ("nedbank.co.za",)},
    "TymeBank": {"text": ("tymebank", "tyme bank", "gotyme"),
                 "host": ("tymebank", "gotyme"),
                 "domains": ("tymebank.co.za", "gotyme.co.za")},
    "SARS": {"text": ("sars", "efiling", "e-filing"),
             "host": ("sars", "efiling"),
             "domains": ("sars.gov.za", "sarsefiling.co.za")},
    "SASSA": {"text": ("sassa",), "host": ("sassa",),
              "domains": ("sassa.gov.za",)},
    "NSFAS": {"text": ("nsfas",), "host": ("nsfas",),
              "domains": ("nsfas.org.za",)},
    "SA Post Office": {"text": ("post office", "postoffice", "sapo"),
                       "host": ("postoffice",),   # not "sapo": sapo.pt is unrelated
                       "domains": ("postoffice.co.za",)},
    "The Courier Guy": {"text": ("courier guy", "courierguy"),
                        "host": ("courierguy",),
                        "domains": ("thecourierguy.co.za",)},
    "PostNet": {"text": ("postnet",), "host": ("postnet",),
                "domains": ("postnet.co.za",)},
    "Vodacom": {"text": ("vodacom",), "host": ("vodacom",),
                "domains": ("vodacom.co.za", "vodacom.com")},
    "MTN": {"text": ("mtn",), "host": ("mtn",),
            "domains": ("mtn.co.za", "mtn.com")},
    "Telkom": {"text": ("telkom",), "host": ("telkom",),
               "domains": ("telkom.co.za",)},
}
_OFFICIAL_DOMAINS = tuple(d for b in BRANDS.values() for d in b["domains"])


def canonical_url(raw: str) -> str:
    """Strip trailing punctuation and add http:// if there is no scheme. Nothing else."""
    url = raw.strip().rstrip(_TRAILING_PUNCT)
    return url if _SCHEME_PATTERN.match(url) else "http://" + url


def has_scheme(url: str) -> bool:
    return bool(_SCHEME_PATTERN.match(url.strip()))


def extract_links(text: str) -> list:
    """LINK_PATTERN matches as written (scheme kept or absent), trailing
    punctuation stripped, de-duplicated in order."""
    links = []
    for m in LINK_PATTERN.findall(text):
        link = m.rstrip(_TRAILING_PUNCT)
        if link and link not in links:
            links.append(link)
    return links


def _on_domain(host: str, domains) -> bool:
    host = host.lower().rstrip(".")
    return any(host == d or host.endswith("." + d) for d in domains)


def is_protected_domain(host: str) -> bool:
    """Shortener or official brand domain: never stored or matched as a
    domain-level threat indicator (one bad bit.ly link must not taint all)."""
    return _on_domain(host, URL_SHORTENERS + _OFFICIAL_DOMAINS)


# Post-model reason codes: (description, weight). Not in FEATURE_ORDER.
POST_MODEL_CODES = {
    "BRAND_LOOKALIKE_DOMAIN": ("Link imitates {brand} but is not {brand}'s official website", 30),
    "BRAND_LINK_MISMATCH":    ("Mentions {brand} but the link leads somewhere else", 20),
}
_BRAND_TEXT_PATTERNS = {
    brand: re.compile(r"\b(?:" + "|".join(map(re.escape, b["text"])) + r")\b", re.I)
    for brand, b in BRANDS.items()
}


def brand_rule(text: str, urls: list):
    """(code, brand) for at most one brand code, or None. Needs a link, so
    genuine brand SMS such as "Your FNB OTP is 123456" never fire.

    BRAND_LOOKALIKE_DOMAIN (checked first): a link's host contains a brand
    keyword but is not on that brand's official domain (fnb-verify.co.za).
    BRAND_LINK_MISMATCH: the text names a brand and no link goes to that
    brand's official domain (shorteners, unrelated hosts).
    """
    if not urls:
        return None
    hosts = [(urlparse(u).hostname or "").lower() for u in urls]
    for host in hosts:
        compact = host.replace("-", "")
        for brand, b in BRANDS.items():
            if any(k in compact for k in b["host"]) and not _on_domain(host, b["domains"]):
                return "BRAND_LOOKALIKE_DOMAIN", brand
    prose = LINK_PATTERN.sub(" ", text)   # a name inside a link is not a mention
    for brand, b in BRANDS.items():
        if (_BRAND_TEXT_PATTERNS[brand].search(prose)
                and not any(_on_domain(h, b["domains"]) for h in hosts)):
            return "BRAND_LINK_MISMATCH", brand
    return None


@dataclass
class RuleResult:
    features: dict          # code -> 0/1
    reasons: list           # fired reason codes with descriptions
    rule_score: int         # 0-100 capped sum of fired weights
    urls: list              # canonical_url() of each LINK_PATTERN match, de-duplicated


def _contains_any(text: str, words) -> bool:
    t = text.lower()
    return any(w in t for w in words)


def _model_rule_flags(text: str) -> dict:
    """The nine model-input rules, keyed in FEATURE_ORDER. Frozen (see above)."""
    caps_ratio = sum(1 for c in text if c.isupper()) / max(len(text), 1)
    return {
        "URL_PRESENT": bool(MODEL_URL_PATTERN.search(text)),
        "URL_SHORTENER": bool(SHORTENER_PATTERN.search(text)),
        "URGENCY_LANGUAGE": _contains_any(text, URGENCY_WORDS),
        "IMPERSONATION": _contains_any(text, IMPERSONATION_WORDS),
        "PRIZE_LURE": _contains_any(text, PRIZE_WORDS),
        "CREDENTIAL_REQUEST": _contains_any(text, CREDENTIAL_WORDS),
        "MONEY_MENTION": bool(CURRENCY_PATTERN.search(text)),
        "SUSPICIOUS_NUMBER": bool(PHONE_PATTERN.search(text)),
        "ALL_CAPS_EMPHASIS": caps_ratio > 0.3 and len(text) > 20,
    }


def extract_rules(text: str) -> RuleResult:
    fired = _model_rule_flags(text)
    urls = list(dict.fromkeys(canonical_url(l) for l in extract_links(text)))

    features = {code: int(v) for code, v in fired.items()}
    reasons = [
        {"code": code, "description": REASON_CODES[code][0]}
        for code, v in fired.items() if v
    ]
    rule_score = sum(REASON_CODES[c][1] for c, v in fired.items() if v)

    # Post-model layer: adds a reason and rule score, never a model feature.
    brand = brand_rule(text, urls)
    if brand:
        code, name = brand
        description, weight = POST_MODEL_CODES[code]
        # First in the list so it survives the 6-code cap in score.py.
        reasons.insert(0, {"code": code, "description": description.format(brand=name)})
        rule_score += weight

    return RuleResult(features=features, reasons=reasons,
                      rule_score=min(100, rule_score), urls=urls)


def rule_feature_vector(text: str):
    """Numeric vector in FEATURE_ORDER, for stacking with TF-IDF (model input)."""
    f = _model_rule_flags(text)
    return [int(f[c]) for c in FEATURE_ORDER]


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
    urls = MODEL_URL_PATTERN.findall(text)
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
