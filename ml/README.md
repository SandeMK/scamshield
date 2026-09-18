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
| F1-score | >= 0.85 | 0.942 (held-out); 5-fold CV model selection: LogReg 0.941 > RF 0.923 > GB 0.915 |
| Reason codes per result | >= 3 | Always >= 3 (rules + ML fallbacks) |

## Hybrid scoring formula
`risk = 100 * (0.6 * ml_probability + 0.4 * rule_score/100)`

Labels: >=90 CRITICAL, >=70 HIGH_RISK, >=40 MEDIUM_RISK, >=20 LOW_RISK, else SAFE.

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
