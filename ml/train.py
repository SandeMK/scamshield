"""
ScamShield model training pipeline.

Hybrid design: TF-IDF text features + rule-based features (from features.py)
feed a Logistic Regression classifier. Evaluated with stratified train/test
split against the proposal's success criterion (F1 >= 0.85).

Usage: python train.py
Outputs: model.joblib (vectorizer + classifier bundle), metrics printed.
"""

import numpy as np
import pandas as pd
import joblib
from scipy.sparse import hstack, csr_matrix
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import (
    f1_score, precision_score, recall_score, accuracy_score,
    classification_report, confusion_matrix,
)

from features import rule_feature_vector, FEATURE_ORDER

RANDOM_STATE = 42
DATA_PATH = "data/sms_spam.tsv"
MODEL_PATH = "model.joblib"


DATA_URL = ("https://raw.githubusercontent.com/justmarkham/"
            "pycon-2016-tutorial/master/data/sms.tsv")


def load_data(path=DATA_PATH) -> pd.DataFrame:
    import os, urllib.request
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        print(f"Dataset not found, downloading UCI SMS Spam Collection ...")
        urllib.request.urlretrieve(DATA_URL, path)
    df = pd.read_csv(path, sep="\t", header=None, names=["label", "text"])
    df["y"] = (df["label"] == "spam").astype(int)
    return df


def build_features(texts, vectorizer=None):
    """TF-IDF + rule features, returns (X, fitted_vectorizer)."""
    if vectorizer is None:
        vectorizer = TfidfVectorizer(
            lowercase=True,
            ngram_range=(1, 2),
            min_df=2,
            sublinear_tf=True,
            strip_accents="unicode",
        )
        X_text = vectorizer.fit_transform(texts)
    else:
        X_text = vectorizer.transform(texts)

    X_rules = csr_matrix(np.array([rule_feature_vector(t) for t in texts]))
    return hstack([X_text, X_rules]).tocsr(), vectorizer


def main():
    df = load_data()
    print(f"Dataset: {len(df)} messages "
          f"({df['y'].sum()} scam / {(1 - df['y']).sum()} legitimate)")

    X_train_txt, X_test_txt, y_train, y_test = train_test_split(
        df["text"].tolist(), df["y"].values,
        test_size=0.2, stratify=df["y"], random_state=RANDOM_STATE,
    )

    X_train, vectorizer = build_features(X_train_txt)
    X_test, _ = build_features(X_test_txt, vectorizer)

    clf = LogisticRegression(
        max_iter=2000, C=10.0, class_weight="balanced", random_state=RANDOM_STATE
    )
    clf.fit(X_train, y_train)

    y_pred = clf.predict(X_test)

    f1 = f1_score(y_test, y_pred)
    print("\n=== Held-out test set (20%) ===")
    print(f"F1-score : {f1:.4f}  (target >= 0.85 -> {'PASS' if f1 >= 0.85 else 'FAIL'})")
    print(f"Precision: {precision_score(y_test, y_pred):.4f}")
    print(f"Recall   : {recall_score(y_test, y_pred):.4f}")
    print(f"Accuracy : {accuracy_score(y_test, y_pred):.4f}")
    print("\nConfusion matrix [rows=true, cols=pred] (ham, spam):")
    print(confusion_matrix(y_test, y_pred))
    print("\n" + classification_report(y_test, y_pred, target_names=["ham", "scam"]))

    # 5-fold CV on full data for a stability check (refit per fold would be
    # ideal; this is an approximation using the fitted vectorizer space).
    X_all, _ = build_features(df["text"].tolist(), vectorizer)
    cv_f1 = cross_val_score(clf, X_all, df["y"].values, cv=5, scoring="f1")
    print(f"5-fold CV F1: mean={cv_f1.mean():.4f}  std={cv_f1.std():.4f}")

    joblib.dump(
        {"vectorizer": vectorizer, "classifier": clf, "feature_order": FEATURE_ORDER},
        MODEL_PATH,
    )
    print(f"\nModel bundle saved -> {MODEL_PATH}")


if __name__ == "__main__":
    main()
