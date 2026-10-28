"""Model-input regression guard (A4 build brief §1).

The committed model.joblib was trained on full_feature_vector() output.
Any change to MODEL_URL_PATTERN, FEATURE_ORDER or the nine model rules
changes what the model sees and silently invalidates the reported F1.

1. Feature vectors for every UCI message must match, bit for bit, a
   snapshot taken before the A4 rule changes.
2. The committed model's held-out results (no refit) must be unchanged.

Regenerate the snapshot ONLY after a deliberate retrain:
    cd ml && python tests/test_model_regression.py --write
"""

import hashlib
import os
import sys

import numpy as np

ML_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ML_DIR)

from features import full_feature_vector, FEATURE_ORDER, ENGINEERED_ORDER  # noqa: E402
from train import load_data  # noqa: E402

DATA_PATH = os.path.join(ML_DIR, "data", "sms_spam.tsv")
MODEL_PATH = os.path.join(ML_DIR, "model.joblib")
SNAPSHOT_PATH = os.path.join(ML_DIR, "tests", "fixtures",
                             "feature_vectors_v1.0.0.npz")

# Held-out results of the committed RandomForest v1.0.0 (docs/RESULTS.md).
EXPECTED_F1 = 0.9338
EXPECTED_CONFUSION = [[962, 4], [15, 134]]   # rows = true (ham, scam)


def _dataset_digest(df) -> str:
    h = hashlib.sha256()
    for label, text in zip(df["label"], df["text"]):
        h.update(f"{label}\t{text}\n".encode("utf-8"))
    return h.hexdigest()


def _all_vectors(df) -> np.ndarray:
    return np.array([full_feature_vector(t) for t in df["text"]],
                    dtype=np.float64)


def test_feature_vectors_unchanged_over_full_dataset():
    snap = np.load(SNAPSHOT_PATH)
    df = load_data(DATA_PATH)
    assert _dataset_digest(df) == str(snap["dataset_sha256"]), \
        "UCI dataset differs from the one the snapshot was taken on"
    assert list(snap["feature_order"]) == FEATURE_ORDER + ENGINEERED_ORDER

    current = _all_vectors(df)
    expected = snap["vectors"]
    assert current.shape == expected.shape
    diff_rows = np.where((current != expected).any(axis=1))[0]
    assert diff_rows.size == 0, (
        f"{diff_rows.size} of {len(df)} feature vectors changed; first: "
        + "; ".join(repr(df['text'].iloc[i][:60]) for i in diff_rows[:3]))


def test_committed_model_heldout_results_unchanged():
    from evaluate import evaluate
    res = evaluate(MODEL_PATH, DATA_PATH)
    assert res["model_name"] == "RandomForest"
    assert res["model_version"] == "v1.0.0"
    assert round(res["f1"], 4) == EXPECTED_F1
    assert res["confusion_matrix"] == EXPECTED_CONFUSION


if __name__ == "__main__" and "--write" in sys.argv:
    df = load_data(DATA_PATH)
    os.makedirs(os.path.dirname(SNAPSHOT_PATH), exist_ok=True)
    np.savez_compressed(
        SNAPSHOT_PATH,
        vectors=_all_vectors(df),
        dataset_sha256=np.array(_dataset_digest(df)),
        feature_order=np.array(FEATURE_ORDER + ENGINEERED_ORDER),
    )
    print(f"Snapshot of {len(df)} vectors written -> {SNAPSHOT_PATH}")
