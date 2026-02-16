"""
Sklearn Iris Classifier — Training Pipeline.

Trains a RandomForestClassifier on the Iris dataset, evaluates accuracy,
and saves the model as a ``.pkl`` artifact ready for Aquilia MLOps packaging.

Usage::

    python -m modules.mlops.train           # from myapp/
    # or
    from modules.mlops.train import train_iris_model
    model, metrics, path = train_iris_model()
"""

from __future__ import annotations

import json
import logging
import os
import pickle
import time
from pathlib import Path
from typing import Any, Dict, Tuple

import numpy as np
from sklearn.datasets import load_iris
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.model_selection import train_test_split

logger = logging.getLogger("myapp.mlops.train")

# ── Constants ──────────────────────────────────────────────────────────

ARTIFACTS_DIR = Path(__file__).resolve().parent.parent.parent / "artifacts" / "mlops"
MODEL_NAME = "iris-classifier"
MODEL_VERSION = "v1.0.0"


def train_iris_model(
    *,
    n_estimators: int = 100,
    max_depth: int | None = 5,
    test_size: float = 0.2,
    random_state: int = 42,
    output_dir: str | Path | None = None,
) -> Tuple[RandomForestClassifier, Dict[str, Any], Path]:
    """
    Train a RandomForest on the Iris dataset.

    Returns:
        Tuple of (fitted model, evaluation metrics dict, path to .pkl).
    """
    out = Path(output_dir) if output_dir else ARTIFACTS_DIR
    out.mkdir(parents=True, exist_ok=True)

    # ── Load & split ────────────────────────────────────────────────
    iris = load_iris()
    X_train, X_test, y_train, y_test = train_test_split(
        iris.data, iris.target,
        test_size=test_size,
        random_state=random_state,
        stratify=iris.target,
    )

    # ── Train ───────────────────────────────────────────────────────
    logger.info("Training RandomForest (n=%d, depth=%s) …", n_estimators, max_depth)
    t0 = time.perf_counter()

    model = RandomForestClassifier(
        n_estimators=n_estimators,
        max_depth=max_depth,
        random_state=random_state,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)
    train_time = time.perf_counter() - t0

    # ── Evaluate ────────────────────────────────────────────────────
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred, average="weighted")
    report = classification_report(
        y_test, y_pred,
        target_names=list(iris.target_names),
        output_dict=True,
    )

    metrics = {
        "accuracy": float(accuracy),
        "f1_weighted": float(f1),
        "train_time_s": round(train_time, 4),
        "n_estimators": n_estimators,
        "max_depth": max_depth,
        "n_train": len(X_train),
        "n_test": len(X_test),
        "feature_names": list(iris.feature_names),
        "target_names": list(iris.target_names),
        "classification_report": report,
    }

    # ── Save ────────────────────────────────────────────────────────
    model_path = out / "model.pkl"
    with open(model_path, "wb") as f:
        pickle.dump(model, f, protocol=pickle.HIGHEST_PROTOCOL)

    metrics_path = out / "metrics.json"
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)

    logger.info(
        "Model saved → %s  (accuracy=%.4f, f1=%.4f, train=%.2fs)",
        model_path, accuracy, f1, train_time,
    )
    return model, metrics, model_path


# ── CLI entrypoint ──────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    model, metrics, path = train_iris_model()
    print(f"\n✓ Model saved to {path}")
    print(f"  accuracy : {metrics['accuracy']:.4f}")
    print(f"  f1       : {metrics['f1_weighted']:.4f}")
    print(f"  train    : {metrics['train_time_s']:.4f}s")
    print(f"  features : {metrics['feature_names']}")
    print(f"  targets  : {metrics['target_names']}")
