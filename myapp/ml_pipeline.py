"""
Nexus Platform — Product Recommendation Model Training Pipeline

Uses scikit-learn to build a product recommendation / purchase prediction
model, then packages it via Aquilia MLOps ModelpackBuilder and deploys it
through RegistryService + PythonRuntime.

Pipeline stages:
  1. Generate synthetic e-commerce dataset
  2. Feature engineering
  3. Train / test split
  4. Model selection (RandomForest, GradientBoosting, LogisticRegression)
  5. Hyperparameter tuning via GridSearchCV
  6. Evaluation (accuracy, precision, recall, F1, ROC-AUC)
  7. Export model as .pkl
  8. Build .aquilia modelpack archive
  9. Register in Aquilia MLOps registry
 10. Serve via PythonRuntime
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import pickle
import sys
from pathlib import Path
from datetime import datetime, timezone

import numpy as np
from sklearn.datasets import make_classification
from sklearn.ensemble import (
    GradientBoostingClassifier,
    RandomForestClassifier,
)
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import GridSearchCV, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("nexus.ml_pipeline")

# ─── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
MODEL_DIR = BASE_DIR / "runtime" / "models"
DIST_DIR = BASE_DIR / "runtime" / "dist"


# ═══════════════════════════════════════════════════════════════════════════════
#  STAGE 1: Synthetic Dataset Generation
# ═══════════════════════════════════════════════════════════════════════════════

def generate_ecommerce_dataset(
    n_samples: int = 5000,
    n_features: int = 12,
    random_state: int = 42,
) -> tuple:
    """
    Generate a synthetic e-commerce purchase-prediction dataset.

    Features simulate:
      - user_activity_score     : browsing intensity (0-1)
      - cart_value              : total cart value
      - page_views              : product page views count
      - time_on_site_minutes    : session duration
      - previous_purchases      : historical purchase count
      - wishlist_count          : items in wishlist
      - discount_applied        : discount percentage
      - category_affinity       : affinity score for top category
      - device_is_mobile        : 0/1 binary
      - referral_source_score   : referral quality (0-1)
      - email_engagement        : email open rate
      - days_since_last_visit   : recency

    Target: will_purchase (0/1)
    """
    logger.info("Generating synthetic e-commerce dataset: %d samples, %d features", n_samples, n_features)

    X, y = make_classification(
        n_samples=n_samples,
        n_features=n_features,
        n_informative=9,
        n_redundant=2,
        n_clusters_per_class=2,
        weights=[0.6, 0.4],
        flip_y=0.05,
        random_state=random_state,
    )

    feature_names = [
        "user_activity_score",
        "cart_value",
        "page_views",
        "time_on_site_minutes",
        "previous_purchases",
        "wishlist_count",
        "discount_applied",
        "category_affinity",
        "device_is_mobile",
        "referral_source_score",
        "email_engagement",
        "days_since_last_visit",
    ]

    # Rescale features to realistic ranges
    ranges = {
        "user_activity_score": (0, 1),
        "cart_value": (5, 500),
        "page_views": (1, 50),
        "time_on_site_minutes": (0.5, 120),
        "previous_purchases": (0, 30),
        "wishlist_count": (0, 15),
        "discount_applied": (0, 50),
        "category_affinity": (0, 1),
        "device_is_mobile": (0, 1),
        "referral_source_score": (0, 1),
        "email_engagement": (0, 1),
        "days_since_last_visit": (0, 90),
    }

    for i, name in enumerate(feature_names):
        lo, hi = ranges[name]
        col = X[:, i]
        col = (col - col.min()) / (col.max() - col.min() + 1e-8)
        X[:, i] = col * (hi - lo) + lo

    # Binary columns
    X[:, feature_names.index("device_is_mobile")] = (
        X[:, feature_names.index("device_is_mobile")] > 0.5
    ).astype(float)

    logger.info(
        "Dataset generated: %d samples, positive rate: %.1f%%",
        n_samples, y.mean() * 100,
    )

    return X, y, feature_names


# ═══════════════════════════════════════════════════════════════════════════════
#  STAGE 2 & 3: Feature Engineering + Train/Test Split
# ═══════════════════════════════════════════════════════════════════════════════

def prepare_data(X, y, test_size: float = 0.2, random_state: int = 42):
    """Split into train/test with stratification."""
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y,
    )
    logger.info(
        "Train/Test split: train=%d, test=%d (%.0f%%/%.0f%%)",
        len(X_train), len(X_test),
        (1 - test_size) * 100, test_size * 100,
    )
    return X_train, X_test, y_train, y_test


# ═══════════════════════════════════════════════════════════════════════════════
#  STAGE 4 & 5: Model Selection + Hyperparameter Tuning
# ═══════════════════════════════════════════════════════════════════════════════

def train_models(X_train, y_train):
    """
    Train multiple models with hyperparameter tuning.
    Returns (best_model_name, best_pipeline, all_results).
    """
    logger.info("=" * 70)
    logger.info("MODEL SELECTION & HYPERPARAMETER TUNING")
    logger.info("=" * 70)

    candidates = {
        "RandomForest": {
            "pipeline": Pipeline([
                ("scaler", StandardScaler()),
                ("clf", RandomForestClassifier(random_state=42)),
            ]),
            "params": {
                "clf__n_estimators": [100, 200],
                "clf__max_depth": [10, 20, None],
                "clf__min_samples_split": [2, 5],
                "clf__min_samples_leaf": [1, 2],
            },
        },
        "GradientBoosting": {
            "pipeline": Pipeline([
                ("scaler", StandardScaler()),
                ("clf", GradientBoostingClassifier(random_state=42)),
            ]),
            "params": {
                "clf__n_estimators": [100, 200],
                "clf__max_depth": [3, 5, 7],
                "clf__learning_rate": [0.05, 0.1],
                "clf__subsample": [0.8, 1.0],
            },
        },
        "LogisticRegression": {
            "pipeline": Pipeline([
                ("scaler", StandardScaler()),
                ("clf", LogisticRegression(max_iter=1000, random_state=42)),
            ]),
            "params": {
                "clf__C": [0.01, 0.1, 1.0, 10.0],
                "clf__penalty": ["l2"],
                "clf__solver": ["lbfgs"],
            },
        },
    }

    results = {}
    best_score = -1
    best_name = ""
    best_pipeline = None

    for name, config in candidates.items():
        logger.info("\n─── Training: %s ───", name)

        grid = GridSearchCV(
            config["pipeline"],
            config["params"],
            cv=5,
            scoring="f1",
            n_jobs=-1,
            verbose=0,
        )
        grid.fit(X_train, y_train)

        cv_scores = cross_val_score(grid.best_estimator_, X_train, y_train, cv=5, scoring="f1")

        results[name] = {
            "best_params": grid.best_params_,
            "best_cv_f1": grid.best_score_,
            "cv_f1_mean": cv_scores.mean(),
            "cv_f1_std": cv_scores.std(),
            "estimator": grid.best_estimator_,
        }

        logger.info("  Best params: %s", grid.best_params_)
        logger.info("  CV F1: %.4f (±%.4f)", cv_scores.mean(), cv_scores.std())

        if grid.best_score_ > best_score:
            best_score = grid.best_score_
            best_name = name
            best_pipeline = grid.best_estimator_

    logger.info("\n" + "=" * 70)
    logger.info("WINNER: %s (CV F1: %.4f)", best_name, best_score)
    logger.info("=" * 70)

    return best_name, best_pipeline, results


# ═══════════════════════════════════════════════════════════════════════════════
#  STAGE 6: Evaluation
# ═══════════════════════════════════════════════════════════════════════════════

def evaluate_model(model, X_test, y_test, model_name: str) -> dict:
    """Comprehensive evaluation of the best model."""
    logger.info("\n" + "=" * 70)
    logger.info("MODEL EVALUATION: %s", model_name)
    logger.info("=" * 70)

    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred)
    recall = recall_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)
    roc_auc = roc_auc_score(y_test, y_proba)

    logger.info("  Accuracy:  %.4f", accuracy)
    logger.info("  Precision: %.4f", precision)
    logger.info("  Recall:    %.4f", recall)
    logger.info("  F1-Score:  %.4f", f1)
    logger.info("  ROC-AUC:   %.4f", roc_auc)

    report = classification_report(y_test, y_pred, target_names=["no_purchase", "purchase"])
    logger.info("\nClassification Report:\n%s", report)

    cm = confusion_matrix(y_test, y_pred)
    logger.info("Confusion Matrix:\n%s", cm)

    metrics = {
        "accuracy": float(accuracy),
        "precision": float(precision),
        "recall": float(recall),
        "f1_score": float(f1),
        "roc_auc": float(roc_auc),
        "confusion_matrix": cm.tolist(),
    }
    return metrics


# ═══════════════════════════════════════════════════════════════════════════════
#  STAGE 7: Export Model
# ═══════════════════════════════════════════════════════════════════════════════

def export_model(model, feature_names: list, metrics: dict, model_name: str) -> Path:
    """Serialize model + metadata to .pkl file."""
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    model_path = MODEL_DIR / "purchase_predictor.pkl"

    # Wrap the model with metadata for the PythonRuntime
    model_bundle = {
        "model": model,
        "feature_names": feature_names,
        "model_name": model_name,
        "metrics": metrics,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "version": "v1.0.0",
    }

    with open(model_path, "wb") as f:
        pickle.dump(model_bundle, f)

    size_mb = model_path.stat().st_size / (1024 * 1024)
    logger.info("Model exported: %s (%.2f MB)", model_path, size_mb)

    # Also export feature names as JSON for the serving runtime
    meta_path = MODEL_DIR / "model_metadata.json"
    with open(meta_path, "w") as f:
        json.dump({
            "model_name": model_name,
            "feature_names": feature_names,
            "n_features": len(feature_names),
            "metrics": metrics,
            "framework": "sklearn",
            "version": "v1.0.0",
        }, f, indent=2)

    logger.info("Metadata exported: %s", meta_path)
    return model_path


# ═══════════════════════════════════════════════════════════════════════════════
#  STAGE 8: Build .aquilia Modelpack
# ═══════════════════════════════════════════════════════════════════════════════

async def build_modelpack(model_path: Path, metrics: dict) -> str:
    """Build an .aquilia archive using ModelpackBuilder."""
    from aquilia.mlops import ModelpackBuilder
    from aquilia.mlops._types import TensorSpec

    DIST_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("\n" + "=" * 70)
    logger.info("BUILDING AQUILIA MODELPACK")
    logger.info("=" * 70)

    # Create a requirements lock file
    reqs_path = MODEL_DIR / "requirements.txt"
    reqs_path.write_text("scikit-learn>=1.3.0\nnumpy>=1.24.0\njoblib>=1.3.0\n")

    builder = ModelpackBuilder(
        name="nexus-purchase-predictor",
        version="v1.0.0",
        framework="sklearn",
    )

    builder.add_model(str(model_path), framework="sklearn")
    builder.add_file(str(MODEL_DIR / "model_metadata.json"))
    builder.add_env_lock(str(reqs_path))

    builder.set_signature(
        inputs=[TensorSpec("features", "float64", [None, 12])],
        outputs=[TensorSpec("prediction", "int64", [None, 1])],
    )

    builder.set_provenance(
        git_sha="local-training",
        dataset_snapshot="synthetic-ecommerce-v1",
    )

    builder.set_metadata(
        accuracy=metrics["accuracy"],
        f1_score=metrics["f1_score"],
        roc_auc=metrics["roc_auc"],
        task="purchase_prediction",
        domain="e-commerce",
    )

    pack_path = await builder.save(str(DIST_DIR))
    logger.info("Modelpack built: %s", pack_path)
    return pack_path


# ═══════════════════════════════════════════════════════════════════════════════
#  STAGE 9: Register in Aquilia MLOps Registry
# ═══════════════════════════════════════════════════════════════════════════════

async def register_model(pack_path: str) -> None:
    """Register the modelpack in Aquilia's RegistryService."""
    from aquilia.mlops import ModelpackBuilder, RegistryService

    logger.info("\n" + "=" * 70)
    logger.info("REGISTERING MODEL IN AQUILIA REGISTRY")
    logger.info("=" * 70)

    # Unpack to read manifest
    unpack_dir = DIST_DIR / "unpacked"
    manifest = await ModelpackBuilder.unpack(pack_path, str(unpack_dir))
    logger.info("Unpacked manifest: %s v%s", manifest.name, manifest.version)

    # Initialize registry
    registry_db = str(BASE_DIR / "runtime" / "models_registry.db")
    blob_root = str(BASE_DIR / "runtime" / ".nexus-models")

    registry = RegistryService(db_path=registry_db, blob_root=blob_root)
    await registry.initialize()

    # Publish
    await registry.publish(manifest)
    logger.info("Model published to registry: %s v%s", manifest.name, manifest.version)

    # Verify
    fetched = await registry.fetch(manifest.name, manifest.version)
    logger.info("Registry verification: %s v%s ✓", fetched.name, fetched.version)

    versions = await registry.list_versions(manifest.name)
    logger.info("Available versions: %s", versions)

    await registry.close()


# ═══════════════════════════════════════════════════════════════════════════════
#  STAGE 10: Deploy via PythonRuntime (verification)
# ═══════════════════════════════════════════════════════════════════════════════

async def deploy_and_verify(pack_path: str, X_test, y_test) -> None:
    """Deploy model via PythonRuntime and verify predictions."""
    from aquilia.mlops import ModelpackBuilder, PythonRuntime
    from aquilia.mlops._types import BatchRequest, InferenceRequest

    logger.info("\n" + "=" * 70)
    logger.info("DEPLOYING MODEL VIA AQUILIA PYTHONRUNTIME")
    logger.info("=" * 70)

    # Unpack
    deploy_dir = DIST_DIR / "deployed"
    manifest = await ModelpackBuilder.unpack(pack_path, str(deploy_dir))
    logger.info("Deploying: %s v%s (framework=%s)", manifest.name, manifest.version, manifest.framework)

    # Custom predict function for sklearn pipeline
    import pickle as _pickle
    model_file = deploy_dir / "model" / manifest.entrypoint
    with open(model_file, "rb") as f:
        bundle = _pickle.load(f)

    sklearn_model = bundle["model"]
    feature_names = bundle["feature_names"]

    def predict_fn(inputs: dict) -> dict:
        """Custom predict function wrapping the sklearn pipeline."""
        features = inputs.get("features", [])
        if isinstance(features, list):
            features = np.array(features)
        if features.ndim == 1:
            features = features.reshape(1, -1)

        predictions = sklearn_model.predict(features).tolist()
        probabilities = sklearn_model.predict_proba(features).tolist()

        return {
            "predictions": predictions,
            "probabilities": probabilities,
            "model": manifest.name,
            "version": manifest.version,
        }

    # Create runtime with custom predict function
    runtime = PythonRuntime(predict_fn=predict_fn)
    await runtime.prepare(manifest, str(deploy_dir))
    await runtime.load()
    logger.info("PythonRuntime loaded successfully")

    # Run verification inference
    sample_indices = np.random.choice(len(X_test), size=min(10, len(X_test)), replace=False)

    correct = 0
    total = len(sample_indices)

    for idx in sample_indices:
        features = X_test[idx].tolist()
        req = InferenceRequest(
            request_id=f"verify-{idx}",
            inputs={"features": features},
        )
        batch = BatchRequest(requests=[req], batch_id=f"verify-batch-{idx}")
        results = await runtime.infer(batch)

        outputs = results[0].outputs
        # PythonRuntime wraps dict results directly; non-dict under "prediction"
        preds = outputs.get("predictions", outputs.get("prediction", {}).get("predictions", []))
        pred = preds[0] if preds else -1
        actual = int(y_test[idx])

        if pred == actual:
            correct += 1
        logger.info(
            "  Sample %d: pred=%d, actual=%d, latency=%.2fms %s",
            idx, pred, actual, results[0].latency_ms,
            "✓" if pred == actual else "✗",
        )

    accuracy = correct / total * 100
    logger.info("\nVerification accuracy: %d/%d (%.1f%%)", correct, total, accuracy)

    # Get runtime metrics
    rt_metrics = await runtime.metrics()
    logger.info("Runtime metrics: %s", json.dumps(rt_metrics, indent=2))

    await runtime.unload()
    logger.info("PythonRuntime unloaded")


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN PIPELINE ORCHESTRATION
# ═══════════════════════════════════════════════════════════════════════════════

async def main():
    """Orchestrate the full ML pipeline."""
    logger.info("=" * 70)
    logger.info("NEXUS PLATFORM — ML PIPELINE")
    logger.info("Purchase Prediction Model (scikit-learn → Aquilia MLOps)")
    logger.info("=" * 70)

    # Stage 1: Generate dataset
    X, y, feature_names = generate_ecommerce_dataset(n_samples=5000, n_features=12)

    # Stage 2-3: Prepare data
    X_train, X_test, y_train, y_test = prepare_data(X, y)

    # Stage 4-5: Train & tune models
    best_name, best_model, all_results = train_models(X_train, y_train)

    # Print comparison table
    logger.info("\n" + "=" * 70)
    logger.info("MODEL COMPARISON")
    logger.info("=" * 70)
    logger.info("%-25s %-12s %-12s", "Model", "CV F1", "Std")
    logger.info("-" * 50)
    for name, res in all_results.items():
        marker = " ← BEST" if name == best_name else ""
        logger.info(
            "%-25s %-12.4f %-12.4f%s",
            name, res["cv_f1_mean"], res["cv_f1_std"], marker,
        )

    # Stage 6: Evaluate
    metrics = evaluate_model(best_model, X_test, y_test, best_name)

    # Stage 7: Export
    model_path = export_model(best_model, feature_names, metrics, best_name)

    # Stage 8: Build modelpack
    pack_path = await build_modelpack(model_path, metrics)

    # Stage 9: Register
    await register_model(pack_path)

    # Stage 10: Deploy & verify
    await deploy_and_verify(pack_path, X_test, y_test)

    logger.info("\n" + "=" * 70)
    logger.info("PIPELINE COMPLETE")
    logger.info("Model: %s | Pack: %s", best_name, pack_path)
    logger.info("=" * 70)

    return pack_path


if __name__ == "__main__":
    asyncio.run(main())
