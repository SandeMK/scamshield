# ScamShield — ML Detection Engine (Component 1)

Hybrid scam-SMS detection: TF-IDF + Logistic Regression combined with an
explainable rule engine. This module is imported by the Cloud Threat Scoring
API (Component 2) and is the basis of the reason codes shown in the Android app.

## Files
- `features.py` — rule engine; each rule = one numeric feature + one reason code
- `train.py`    — training pipeline + evaluation
- `score.py`    — `ScamScorer` class: returns risk score (0-100), label, reasons
- `model.joblib`— trained vectorizer + classifier bundle
- `data/sms_spam.tsv` — UCI SMS Spam Collection (5,572 labeled messages)

## Results vs proposal success criteria
| Criterion | Target | Achieved |
|---|---|---|
| Dataset size | >= 500 samples | 5,572 |
| F1-score | >= 0.85 | 0.956 (held-out), 0.945 +/- 0.010 (5-fold CV) |
| Reason codes per result | >= 3 | Always >= 3 (rules + ML fallbacks) |

## Hybrid scoring formula
`risk = 100 * (0.7 * ml_probability + 0.3 * rule_score/100)`

Labels: >=80 HIGH_RISK, >=50 SUSPICIOUS, >=20 LOW_RISK, else LIKELY_SAFE.

## Run it
```bash
pip install scikit-learn pandas numpy joblib
python train.py     # retrains and saves model.joblib
python score.py     # demo on sample SA smishing messages
```

## Known limitation (document in Assignment 2)
Legitimate OTP messages can score SUSPICIOUS (shared vocabulary with
credential phishing). Mitigations: sender-shortcode whitelist, an OTP-format
rule, and the in-app false-positive reporting loop feeding the shared DB.

## Next components
2. FastAPI Cloud Threat Scoring API (imports `ScamScorer`)
3. Supabase threat-intelligence DB (hashed indicators, reputation)
4. URLhaus + OpenPhish ingestion pipeline
5. Android app  6. Analytics dashboard  7. Mock fintech client
