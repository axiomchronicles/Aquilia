"""
Aquilia MLOps — End-to-End Sklearn Demo.

Runs the full lifecycle:

  1. Train   — Iris RandomForest (sklearn)
  2. Pack    — Build .aquilia modelpack
  3. Deploy  — Spin up ModelServingServer + PythonRuntime
  4. Predict — Run real inference (individual + batch)
  5. Health  — Hit liveness/readiness/health probes
  6. Lineage — Inspect model lineage DAG
  7. Experiment — Create/conclude an A/B test
  8. Metrics — Collect inference metrics
  9. Cleanup — Undeploy

Usage::

    cd myapp && python -m modules.mlops.demo
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-5s %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("demo")


# ── Colour helpers ──────────────────────────────────────────────────────

def _c(code: int, text: str) -> str:
    return f"\033[{code}m{text}\033[0m"

def green(t: str) -> str: return _c(32, t)
def cyan(t: str) -> str: return _c(36, t)
def yellow(t: str) -> str: return _c(33, t)
def bold(t: str) -> str: return _c(1, t)
def dim(t: str) -> str: return _c(2, t)


def banner(title: str) -> None:
    w = 62
    print(f"\n{'─' * w}")
    print(f"  {bold(title)}")
    print(f"{'─' * w}")


def pp(data) -> None:
    """Pretty-print a dict/list."""
    print(json.dumps(data, indent=2, default=str))


# ── Main ────────────────────────────────────────────────────────────────

async def main() -> None:
    from modules.mlops.services import MlopsService

    svc = MlopsService()

    # ── 1. Train ─────────────────────────────────────────────────────
    banner("1 · TRAIN — Iris RandomForest (sklearn)")
    t0 = time.perf_counter()
    metrics = await svc.train(n_estimators=120, max_depth=6)
    print(f"  accuracy  : {green(f'{metrics['accuracy']:.4f}')}")
    print(f"  f1        : {green(f'{metrics['f1_weighted']:.4f}')}")
    print(f"  train time: {metrics['train_time_s']:.4f}s")
    print(f"  features  : {metrics['feature_names']}")
    print(f"  targets   : {metrics['target_names']}")
    print(f"  elapsed   : {time.perf_counter() - t0:.3f}s")

    # ── 2. Pack ──────────────────────────────────────────────────────
    banner("2 · PACK — Build .aquilia modelpack")
    pack = await svc.pack(version="v1.0.0")
    print(f"  archive : {cyan(pack['pack_path'])}")
    print(f"  model   : {pack['name']} {pack['version']}")
    print(f"  framework: {pack['framework']}")

    # ── 3. Deploy ────────────────────────────────────────────────────
    banner("3 · DEPLOY — ModelServingServer + PythonRuntime + WarmUp")
    deploy = await svc.deploy(version="v1.0.0")
    print(f"  status  : {green(deploy['status'])}")
    print(f"  model   : {deploy['model']} {deploy['version']}")
    print(f"  ready   : {deploy['ready']}")

    # ── 4. Health probes ─────────────────────────────────────────────
    banner("4 · HEALTH PROBES")
    live = await svc.liveness()
    ready = await svc.readiness()
    health = await svc.health()
    print(f"  liveness : {green(live['status'])}")
    print(f"  readiness: {green(ready['status'])}")
    print(f"  health   : {green(health['status'])}")

    # ── 5. Predict — single samples ─────────────────────────────────
    banner("5 · PREDICT — Single samples")
    test_samples = [
        ([5.1, 3.5, 1.4, 0.2], "setosa"),       # Classic setosa
        ([7.0, 3.2, 4.7, 1.4], "versicolor"),    # Classic versicolor
        ([6.3, 3.3, 6.0, 2.5], "virginica"),     # Classic virginica
        ([5.9, 3.0, 5.1, 1.8], "virginica"),     # Borderline
        ([4.9, 3.1, 1.5, 0.1], "setosa"),        # Another setosa
    ]

    correct = 0
    for features, expected in test_samples:
        result = await svc.predict(features)
        pred = result["prediction"]
        predicted_class = pred.get("classes", ["?"])[0] if isinstance(pred, dict) else str(pred)
        is_correct = predicted_class == expected
        if is_correct:
            correct += 1
        mark = green("✓") if is_correct else yellow("✗")
        print(f"  {mark} {features} → {cyan(predicted_class)} "
              f"(expected: {expected}) [{result['latency_ms']:.2f}ms]")

    print(f"\n  Score: {correct}/{len(test_samples)} correct")

    # ── 6. Predict — batch ───────────────────────────────────────────
    banner("6 · PREDICT — Batch inference")
    batch_features = [s[0] for s in test_samples]
    batch_results = await svc.predict_batch(batch_features)
    print(f"  Batch size   : {len(batch_results)}")
    total_lat = sum(r["latency_ms"] for r in batch_results)
    print(f"  Total latency: {total_lat:.2f}ms")
    print(f"  Avg latency  : {total_lat / len(batch_results):.2f}ms")

    # ── 7. Lineage ───────────────────────────────────────────────────
    banner("7 · LINEAGE — Model provenance DAG")
    lin = await svc.lineage()
    print(f"  Total nodes: {lin['total_nodes']}")
    print(f"  Roots      : {lin['roots']}")
    print(f"  Leaves     : {lin['leaves']}")
    print(f"  Graph:")
    pp(lin["graph"])

    # ── 8. Experiments ───────────────────────────────────────────────
    banner("8 · EXPERIMENTS — A/B testing")
    exp = await svc.create_experiment(
        experiment_id="iris-rf-vs-gb",
        arms=[
            {"name": "random_forest", "model_version": "v1.0.0", "weight": 0.5},
            {"name": "gradient_boost", "model_version": "v2.0.0", "weight": 0.5},
        ],
        description="Compare RandomForest vs GradientBoosting on Iris",
    )
    print(f"  Created: {cyan(exp['experiment_id'])}")
    print(f"  Arms   : {[a['name'] for a in exp['arms']]}")
    print(f"  Status : {exp['status']}")

    concluded = await svc.conclude_experiment("iris-rf-vs-gb", winner="random_forest")
    print(f"  Winner : {green(concluded.get('metadata', {}).get('winner', ''))}")
    print(f"  Status : {concluded['status']}")

    # ── 9. Metrics ───────────────────────────────────────────────────
    banner("9 · METRICS — Inference observability")
    m = await svc.get_metrics()
    print(f"  Server request count: {m['server'].get('aquilia_request_count', 0)}")
    print(f"  Avg latency (server): {m['server'].get('aquilia_avg_latency_ms', 0):.2f}ms")
    print(f"  Hot models          : {m['hot_models']}")

    # ── 10. Cleanup ──────────────────────────────────────────────────
    banner("10 · CLEANUP — Undeploy")
    ud = await svc.undeploy()
    print(f"  Status: {green(ud['status'])}")

    # ── Summary ──────────────────────────────────────────────────────
    banner("DEMO COMPLETE ✅")
    print(f"""
  Aquilia MLOps end-to-end lifecycle:
    {green('✓')} Trained sklearn Iris RandomForest (accuracy={metrics['accuracy']:.4f})
    {green('✓')} Built .aquilia modelpack ({pack['name']}:{pack['version']})
    {green('✓')} Deployed with PythonRuntime + WarmupStrategy
    {green('✓')} Health probes: liveness={live['status']}, readiness={ready['status']}
    {green('✓')} Ran {len(test_samples)} individual + {len(batch_results)} batch predictions
    {green('✓')} Lineage DAG: {lin['total_nodes']} nodes
    {green('✓')} A/B experiment: created + concluded (winner={concluded.get('metadata', {}).get('winner')})
    {green('✓')} Metrics collected
    {green('✓')} Clean undeploy
""")


if __name__ == "__main__":
    asyncio.run(main())
