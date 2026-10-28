"""
Evaluate the committed model.joblib on train.py's held-out 20% split.

Loads the saved bundle and only calls predict — it never refits or
overwrites the model, so it reports what is actually deployed.

Usage: python evaluate.py
"""

import joblib
import sklearn
from sklearn.metrics import (
    f1_score, precision_score, recall_score, accuracy_score, confusion_matrix,
)

from train import load_data, heldout_split, build_features, DATA_PATH, MODEL_PATH


def evaluate(model_path=MODEL_PATH, data_path=DATA_PATH) -> dict:
    bundle = joblib.load(model_path)
    _, X_test_txt, _, y_test = heldout_split(load_data(data_path))
    X_test, _ = build_features(X_test_txt, bundle["vectorizer"])
    y_pred = bundle["classifier"].predict(X_test)
    return {
        "model_name": bundle.get("model_name"),
        "model_version": bundle.get("model_version"),
        "sklearn_version": sklearn.__version__,
        "n_test": len(y_test),
        "f1": f1_score(y_test, y_pred),
        "precision": precision_score(y_test, y_pred),
        "recall": recall_score(y_test, y_pred),
        "accuracy": accuracy_score(y_test, y_pred),
        "confusion_matrix": confusion_matrix(y_test, y_pred).tolist(),
    }


def main():
    r = evaluate()
    print(f"Model    : {r['model_name']} {r['model_version']} "
          f"(scikit-learn {r['sklearn_version']})")
    print(f"Held-out : {r['n_test']} messages (20%, stratified, seed 42)")
    print(f"F1-score : {r['f1']:.4f}")
    print(f"Precision: {r['precision']:.4f}")
    print(f"Recall   : {r['recall']:.4f}")
    print(f"Accuracy : {r['accuracy']:.4f}")
    print("Confusion matrix [rows=true, cols=pred] (ham, scam):")
    print(f"  {r['confusion_matrix']}")


if __name__ == "__main__":
    main()
