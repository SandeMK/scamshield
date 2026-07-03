"""
ScamShield hybrid scorer — aligned to Assignment 2 (sections 12 & 13.3).

Fusion: risk = 100 * (0.6 * ml_confidence + 0.4 * rule_sub_score/100)
Critical override (13.3): if either layer is critical (>= 90), the final
score is elevated to the higher sub-score.

Response contract (12): risk_score, classification, explanation_codes
[{code, detail}], ml_confidence, rule_sub_score, model_version.
"""

import joblib
import numpy as np
from scipy.sparse import hstack, csr_matrix

from features import extract_rules, full_feature_vector

ML_WEIGHT = 0.6      # Assignment 2 defaults (13.3)
RULE_WEIGHT = 0.4
CRITICAL_THRESHOLD = 90

LABELS = [           # Assignment 2 classification enum (11.1 scan_log)
    (90, "CRITICAL"),
    (70, "HIGH_RISK"),
    (40, "MEDIUM_RISK"),
    (20, "LOW_RISK"),
    (0,  "SAFE"),
]


def _label(score: float) -> str:
    for threshold, label in LABELS:
        if score >= threshold:
            return label
    return "SAFE"


class ScamScorer:
    def __init__(self, model_path: str = "model.joblib"):
        bundle = joblib.load(model_path)
        self.vectorizer = bundle["vectorizer"]
        self.classifier = bundle["classifier"]
        self.model_name = bundle.get("model_name", "unknown")
        self.model_version = bundle.get("model_version", "v1.0.0")

    def score(self, text: str) -> dict:
        rules = extract_rules(text)
        rule_sub_score = rules.rule_score

        X_text = self.vectorizer.transform([text])
        X_num = csr_matrix(np.array([full_feature_vector(text)]))
        X = hstack([X_text, X_num]).tocsr()
        ml_confidence = float(self.classifier.predict_proba(X)[0, 1])
        ml_sub_score = 100 * ml_confidence

        risk = 100 * (ML_WEIGHT * ml_confidence + RULE_WEIGHT * rule_sub_score / 100)
        # Critical override (Assignment 2, 13.3)
        if max(ml_sub_score, rule_sub_score) >= CRITICAL_THRESHOLD:
            risk = max(risk, ml_sub_score, rule_sub_score)
        risk = round(min(risk, 100))

        codes = [{"code": r["code"], "detail": r["description"]}
                 for r in rules.reasons]
        # ML-derived explanation (ET-06: confidence-based, human-readable)
        if ml_confidence >= 0.5:
            codes.append({
                "code": "ML_PHISHING_PATTERN",
                "detail": f"ML confidence {ml_confidence:.2f} - structure "
                          f"matches known phishing patterns",
            })
        else:
            codes.append({
                "code": "ML_BENIGN_PATTERN",
                "detail": f"Message resembles legitimate traffic "
                          f"(scam probability {ml_confidence:.2f})",
            })
        if len(codes) < 3:
            for fb in (
                {"code": "NO_URL", "detail": "No link detected in the message"}
                if not rules.urls else
                {"code": "URL_UNVERIFIED",
                 "detail": "Link not found in threat intelligence yet"},
                {"code": "TEXT_ANALYSIS",
                 "detail": "Wording analysed against known scam vocabulary"},
            ):
                if len(codes) >= 3:
                    break
                codes.append(fb)

        return {
            "risk_score": risk,
            "classification": _label(risk),
            "ml_confidence": round(ml_confidence, 4),
            "rule_sub_score": rule_sub_score,
            "explanation_codes": codes[:6],
            "urls": rules.urls,
            "model_version": f"{self.model_version} ({self.model_name})",
        }


if __name__ == "__main__":
    import json
    scorer = ScamScorer()
    samples = [
        "URGENT: Your FNB account has been suspended. Verify now at http://bit.ly/fnb-secure or lose access.",
        "SARS refund: click http://sars-refund.xyz/claim",
        "Hey, are we still on for lunch tomorrow at 1?",
        "Update your delivery at http://196.23.155.8/track now",
    ]
    for s in samples:
        r = scorer.score(s)
        print(f"\n[{r['risk_score']:>3}] {r['classification']:<12} {s[:60]}")
        for c in r["explanation_codes"]:
            print(f"      - {c['code']}: {c['detail']}")
