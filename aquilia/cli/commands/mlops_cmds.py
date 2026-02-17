"""
MLOps CLI commands — ``aq pack``, ``aq model``, ``aq deploy``, ``aq observe``,
``aq rollout``, ``aq export``, ``aq plugin``, ``aq lineage``, ``aq experiment``.

Registered into the main ``cli`` group by ``__main__.py``.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

import click


# ── helpers ──────────────────────────────────────────────────────────────

def _run(coro):
    """Run an awaitable — Python 3.14+ compatible."""
    return asyncio.run(coro)


# ═══════════════════════════════════════════════════════════════════════════
# aq pack — model packaging
# ═══════════════════════════════════════════════════════════════════════════

@click.group("pack")
def pack_group():
    """Model packaging commands."""
    pass


@pack_group.command("save")
@click.argument("model_path", type=click.Path(exists=True))
@click.option("--name", "-n", required=True, help="Model name")
@click.option("--version", "-V", required=True, help="Semantic version")
@click.option(
    "--framework",
    "-f",
    type=click.Choice(["pytorch", "tensorflow", "sklearn", "onnx", "custom"]),
    default="custom",
    help="Model framework",
)
@click.option("--env-lock", type=click.Path(exists=True), help="Path to requirements.txt or conda lock")
@click.option("--output", "-o", type=click.Path(), default=".", help="Output directory")
@click.option("--sign-key", type=str, help="HMAC key or path to RSA private key for signing")
def pack_save(model_path, name, version, framework, env_lock, output, sign_key):
    """
    Package a model into an .aquilia archive.

    Examples:
      aq pack save model.pt -n my-model -V v1.0.0 -f pytorch
      aq pack save model.onnx -n my-model -V v2.0.0 -f onnx --env-lock requirements.txt
    """
    from aquilia.mlops.pack.builder import ModelpackBuilder

    builder = ModelpackBuilder(name=name, version=version)
    builder.add_model(model_path, framework=framework)

    if env_lock:
        builder.add_env_lock(env_lock)

    async def _save():
        path = await builder.save(output)
        return path

    path = _run(_save())
    click.echo(click.style(f"✓ Pack saved: {path}", fg="green"))


@pack_group.command("inspect")
@click.argument("archive_path", type=click.Path(exists=True))
def pack_inspect(archive_path):
    """
    Display manifest of an .aquilia archive.

    Examples:
      aq pack inspect my-model-v1.0.0.aquilia
    """
    from aquilia.mlops.pack.builder import ModelpackBuilder

    async def _inspect():
        return await ModelpackBuilder.inspect(archive_path)

    manifest = _run(_inspect())
    click.echo(json.dumps(manifest, indent=2, default=str))


@pack_group.command("verify")
@click.argument("archive_path", type=click.Path(exists=True))
@click.option("--key", required=True, help="HMAC key or path to RSA public key")
def pack_verify(archive_path, key):
    """
    Verify the signature of an .aquilia archive.

    Examples:
      aq pack verify my-model-v1.0.0.aquilia --key mysecret
    """
    from aquilia.mlops.pack.signer import verify_archive, HMACSigner

    async def _verify():
        sig_path = archive_path + ".sig"
        signer = HMACSigner(key)
        return await verify_archive(archive_path, sig_path, signer)

    try:
        valid = _run(_verify())
        if valid:
            click.echo(click.style("✓ Signature valid", fg="green"))
        else:
            click.echo(click.style("✗ Signature invalid", fg="red"))
            sys.exit(1)
    except Exception as e:
        click.echo(click.style(f"✗ Verification failed: {e}", fg="red"))
        sys.exit(1)


@pack_group.command("push")
@click.argument("archive_path", type=click.Path(exists=True))
@click.option("--registry", "-r", default="http://localhost:8080", help="Registry URL")
@click.option("--tag", "-t", multiple=True, help="Additional tags")
def pack_push(archive_path, registry, tag):
    """
    Push a pack to a remote registry.

    Examples:
      aq pack push my-model-v1.0.0.aquilia --registry http://registry.internal
      aq pack push my-model-v1.0.0.aquilia -t production -t stable
    """
    click.echo(f"Pushing {archive_path} to {registry} ...")

    async def _push():
        from aquilia.mlops.registry.service import RegistryService
        from aquilia.mlops.registry.storage.filesystem import FilesystemStorageAdapter

        store_root = Path(registry.replace("http://", "").replace("https://", ""))
        adapter = FilesystemStorageAdapter(root=store_root)
        svc = RegistryService(
            db_path=":memory:",
            blob_root=str(store_root / ".blobs"),
            storage_adapter=adapter,
        )
        await svc.initialize()

        from aquilia.mlops.pack.builder import ModelpackBuilder
        manifest_data = await ModelpackBuilder.inspect(archive_path)
        from aquilia.mlops._types import ModelpackManifest
        manifest = ModelpackManifest.from_dict(manifest_data)
        digest = await svc.publish(manifest, archive_path)

        for t in tag:
            await svc.promote(manifest_data["name"], manifest_data.get("version", "latest"), t)

        return digest

    try:
        digest = _run(_push())
        click.echo(click.style(f"✓ Published — digest: {digest}", fg="green"))
    except Exception as e:
        click.echo(click.style(f"✗ Push failed: {e}", fg="red"))
        sys.exit(1)


# ═══════════════════════════════════════════════════════════════════════════
# aq model — model serving
# ═══════════════════════════════════════════════════════════════════════════

@click.group("model")
def model_group():
    """Model serving commands."""
    pass


@model_group.command("serve")
@click.argument("model_path", type=click.Path(exists=True))
@click.option("--runtime", "-r", type=click.Choice(["python", "onnx", "triton"]), default="python")
@click.option("--host", default="0.0.0.0", help="Bind host")
@click.option("--port", "-p", default=9000, type=int, help="Bind port")
@click.option("--batch-size", default=1, type=int, help="Max batch size")
@click.option("--batch-latency-ms", default=50, type=int, help="Max batch wait (ms)")
def model_serve(model_path, runtime, host, port, batch_size, batch_latency_ms):
    """
    Serve a model with the built-in inference server.

    Examples:
      aq model serve model.pt --runtime python --port 9000
      aq model serve model.onnx --runtime onnx --batch-size 8
    """
    click.echo(f"Starting inference server on {host}:{port} ...")
    click.echo(f"  Runtime: {runtime}")
    click.echo(f"  Model:   {model_path}")
    click.echo(f"  Batch:   {batch_size} / {batch_latency_ms}ms")

    async def _serve():
        from aquilia.mlops.serving.server import ModelServingServer
        from aquilia.mlops._types import ModelpackManifest, TensorSpec, BlobRef, Framework

        fw = runtime if runtime != "python" else "pytorch"
        try:
            fw_enum = Framework(fw)
        except ValueError:
            fw_enum = Framework.CUSTOM
        manifest = ModelpackManifest(
            name=Path(model_path).stem,
            version="local",
            framework=fw_enum.value,
            entrypoint=str(model_path),
            inputs=[TensorSpec(name="input", dtype="float32", shape=[-1])],
            outputs=[TensorSpec(name="output", dtype="float32", shape=[-1])],
            blobs=[BlobRef(digest="local", size=0, path=str(model_path))],
        )
        server = ModelServingServer(
            manifest=manifest,
            model_dir=str(Path(model_path).parent),
            max_batch_size=batch_size,
            max_latency_ms=batch_latency_ms,
        )
        await server.start()

        # Keep alive
        import signal
        stop = asyncio.Event()
        for sig in (signal.SIGINT, signal.SIGTERM):
            asyncio.get_event_loop().add_signal_handler(sig, stop.set)
        click.echo(click.style("✓ Server ready — press Ctrl+C to stop", fg="green"))
        await stop.wait()
        await server.stop()

    try:
        _run(_serve())
    except KeyboardInterrupt:
        click.echo("\nShutting down.")


@model_group.command("health")
@click.option("--url", default="http://localhost:9000", help="Server URL")
def model_health(url):
    """Check model server health."""
    import urllib.request
    try:
        with urllib.request.urlopen(f"{url}/health", timeout=5) as r:
            data = json.loads(r.read())
            click.echo(json.dumps(data, indent=2))
    except Exception as e:
        click.echo(click.style(f"✗ Server unreachable: {e}", fg="red"))
        sys.exit(1)


# ═══════════════════════════════════════════════════════════════════════════
# aq deploy — deployment & rollout
# ═══════════════════════════════════════════════════════════════════════════

@click.group("deploy")
def deploy_group():
    """Deployment and rollout commands."""
    pass


@deploy_group.command("rollout")
@click.argument("model_name")
@click.option("--from-version", required=True, help="Current version")
@click.option("--to-version", required=True, help="Target version")
@click.option(
    "--strategy",
    type=click.Choice(["canary", "blue_green", "shadow", "rolling"]),
    default="canary",
)
@click.option("--steps", default=5, type=int, help="Number of rollout phases")
@click.option("--error-threshold", default=0.05, type=float, help="Auto-rollback error rate")
def deploy_rollout(model_name, from_version, to_version, strategy, steps, error_threshold):
    """
    Start a progressive rollout.

    Examples:
      aq deploy rollout my-model --from-version v1 --to-version v2 --strategy canary
    """
    from aquilia.mlops._types import RolloutConfig, RolloutStrategy
    from aquilia.mlops.release.rollout import RolloutEngine

    config = RolloutConfig(
        from_version=from_version,
        to_version=to_version,
        strategy=RolloutStrategy(strategy),
        percentage=max(1, 100 // steps),
        threshold=error_threshold,
        auto_rollback=True,
        step_interval_seconds=300,
    )

    async def _rollout():
        engine = RolloutEngine()
        state = await engine.start(config)
        return state

    state = _run(_rollout())
    click.echo(click.style(f"✓ Rollout started: {state.id}", fg="green"))
    click.echo(json.dumps({
        "model": model_name,
        "from": from_version,
        "to": to_version,
        "strategy": strategy,
        "initial_percentage": config.percentage,
        "error_threshold": error_threshold,
    }, indent=2))


@deploy_group.command("ci-template")
@click.option("--registry", default="ghcr.io/my-org/models", help="Container registry")
@click.option("--output", "-o", type=click.Path(), default=".", help="Output directory")
def deploy_ci_template(registry, output):
    """
    Generate CI/CD templates (GitHub Actions + Dockerfile).

    Examples:
      aq deploy ci-template --registry ghcr.io/my-org --output .ci/
    """
    from aquilia.mlops.release.ci import generate_ci_workflow, generate_dockerfile

    out = Path(output)
    out.mkdir(parents=True, exist_ok=True)

    workflow = generate_ci_workflow(output_dir=str(out))
    dockerfile = generate_dockerfile(output_dir=str(out))

    (out / "mlops-ci.yml").write_text(workflow)
    (out / "Dockerfile.model").write_text(dockerfile)
    click.echo(click.style(f"✓ Templates written to {out}/", fg="green"))


# ═══════════════════════════════════════════════════════════════════════════
# aq observe — observability
# ═══════════════════════════════════════════════════════════════════════════

@click.group("observe")
def observe_group():
    """Observability and monitoring commands."""
    pass


@observe_group.command("drift")
@click.argument("reference_csv", type=click.Path(exists=True))
@click.argument("current_csv", type=click.Path(exists=True))
@click.option("--method", type=click.Choice(["psi", "ks_test"]), default="psi")
@click.option("--threshold", default=0.2, type=float, help="Drift alert threshold")
def observe_drift(reference_csv, current_csv, method, threshold):
    """
    Detect data drift between reference and current datasets.

    Examples:
      aq observe drift train.csv prod.csv --method psi --threshold 0.25
    """
    import csv

    def _load_csv(path):
        with open(path) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        # Build column arrays
        cols = {}
        for col in rows[0].keys():
            try:
                cols[col] = [float(r[col]) for r in rows]
            except (ValueError, TypeError):
                pass
        return cols

    from aquilia.mlops.observe.drift import DriftDetector
    from aquilia.mlops._types import DriftMethod

    ref_cols = _load_csv(reference_csv)
    cur_cols = _load_csv(current_csv)
    detector = DriftDetector(method=DriftMethod(method), threshold=threshold)

    common = set(ref_cols) & set(cur_cols)
    alerts = []
    for col in sorted(common):
        report = detector.check(ref_cols[col], cur_cols[col], feature_name=col)
        status = click.style("DRIFT", fg="red") if report.is_drifted else click.style("OK", fg="green")
        click.echo(f"  {col:30s}  score={report.score:.4f}  {status}")
        if report.is_drifted:
            alerts.append(col)

    if alerts:
        click.echo(click.style(f"\n  ! Drift detected in: {', '.join(alerts)}", fg="yellow"))
    else:
        click.echo(click.style("\n✓ No drift detected", fg="green"))


@observe_group.command("metrics")
@click.option("--format", "fmt", type=click.Choice(["json", "prometheus"]), default="json")
def observe_metrics(fmt):
    """
    Export current metrics.

    Examples:
      aq observe metrics --format prometheus
    """
    from aquilia.mlops.observe.metrics import MetricsCollector

    collector = MetricsCollector()
    if fmt == "prometheus":
        click.echo(collector.to_prometheus())
    else:
        click.echo(json.dumps(collector.get_summary(), indent=2))


# ═══════════════════════════════════════════════════════════════════════════
# aq export — edge / optimised export
# ═══════════════════════════════════════════════════════════════════════════

@click.group("export")
def export_group():
    """Export and optimise models for edge / production."""
    pass


@export_group.command("onnx")
@click.argument("model_path", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(), required=True, help="Output .onnx path")
@click.option("--opset", default=17, type=int, help="ONNX opset version")
def export_onnx(model_path, output, opset):
    """
    Export a PyTorch model to ONNX.

    Examples:
      aq export onnx model.pt -o model.onnx --opset 17
    """
    click.echo(f"Exporting {model_path} → ONNX (opset {opset}) ...")

    async def _export():
        from aquilia.mlops.optimizer.pipeline import OptimizationPipeline
        pipeline = OptimizationPipeline()
        result = await pipeline.to_onnx(model_path, output, opset_version=opset)
        return result

    try:
        result = _run(_export())
        click.echo(click.style(f"✓ ONNX model saved: {output}", fg="green"))
    except Exception as e:
        click.echo(click.style(f"✗ Export failed: {e}", fg="red"))
        sys.exit(1)


@export_group.command("edge")
@click.argument("model_path", type=click.Path(exists=True))
@click.option(
    "--target",
    type=click.Choice(["tflite", "coreml", "onnx_quantised", "tensorrt"]),
    required=True,
)
@click.option("--output", "-o", type=click.Path(), required=True)
def export_edge(model_path, target, output):
    """
    Export model for edge deployment.

    Examples:
      aq export edge model.onnx --target tflite -o model.tflite
      aq export edge model.onnx --target coreml -o model.mlmodel
    """
    click.echo(f"Exporting {model_path} → {target} ...")

    async def _export():
        from aquilia.mlops.optimizer.export import EdgeExporter
        from aquilia.mlops._types import ExportTarget
        exporter = EdgeExporter()
        return await exporter.export(model_path, ExportTarget(target), output)

    try:
        path = _run(_export())
        click.echo(click.style(f"✓ Edge model saved: {path}", fg="green"))
    except Exception as e:
        click.echo(click.style(f"✗ Export failed: {e}", fg="red"))
        sys.exit(1)


# ═══════════════════════════════════════════════════════════════════════════
# aq plugin — plugin management
# ═══════════════════════════════════════════════════════════════════════════

@click.group("plugin")
def plugin_group():
    """Plugin management commands."""
    pass


@plugin_group.command("list")
def plugin_list():
    """List discovered plugins."""
    from aquilia.mlops.plugins.host import PluginHost

    host = PluginHost()
    host.discover_entrypoints()
    plugins = host.list_plugins()

    if not plugins:
        click.echo("No plugins discovered.")
        return

    click.echo(f"{'Name':30s} {'Version':12s} {'State':15s} Module")
    click.echo("─" * 80)
    for p in plugins:
        click.echo(f"{p.name:30s} {p.version:12s} {p.state.value:15s} {p.module}")


@plugin_group.command("install")
@click.argument("package_name")
def plugin_install(package_name):
    """
    Install a plugin from PyPI.

    Examples:
      aq plugin install aquilia-mlops-drift-monitor
    """
    from aquilia.mlops.plugins.marketplace import PluginMarketplace

    mp = PluginMarketplace()
    ok = mp.install(package_name)
    if ok:
        click.echo(click.style(f"✓ Installed {package_name}", fg="green"))
    else:
        click.echo(click.style(f"✗ Installation failed", fg="red"))
        sys.exit(1)


@plugin_group.command("uninstall")
@click.argument("package_name")
def plugin_uninstall(package_name):
    """Uninstall a plugin."""
    from aquilia.mlops.plugins.marketplace import PluginMarketplace

    mp = PluginMarketplace()
    ok = mp.uninstall(package_name)
    if ok:
        click.echo(click.style(f"✓ Uninstalled {package_name}", fg="green"))
    else:
        click.echo(click.style(f"✗ Uninstallation failed", fg="red"))
        sys.exit(1)


@plugin_group.command("search")
@click.argument("query")
@click.option("--verified-only", is_flag=True, help="Only show verified plugins")
def plugin_search(query, verified_only):
    """
    Search the plugin marketplace.

    Examples:
      aq plugin search drift
      aq plugin search monitoring --verified-only
    """
    from aquilia.mlops.plugins.marketplace import PluginMarketplace

    mp = PluginMarketplace()

    async def _search():
        await mp.fetch_index()
        return mp.search(query, verified_only=verified_only)

    try:
        results = _run(_search())
        if not results:
            click.echo("No plugins found.")
            return
        click.echo(f"{'Name':30s} {'Version':10s} {'Downloads':>10s}  Description")
        click.echo("─" * 90)
        for r in results:
            v = "✓" if r.verified else " "
            click.echo(f"{r.name:30s} {r.version:10s} {r.downloads:>10d}  {v} {r.description[:40]}")
    except Exception as e:
        click.echo(click.style(f"✗ Search failed: {e}", fg="red"))
        sys.exit(1)


# ═══════════════════════════════════════════════════════════════════════════
# aq lineage — model lineage tracking
# ═══════════════════════════════════════════════════════════════════════════

@click.group("lineage")
def lineage_group():
    """Model lineage and provenance tracking commands."""
    pass


@lineage_group.command("show")
@click.option("--format", "fmt", type=click.Choice(["tree", "json"]), default="tree")
def lineage_show(fmt):
    """
    Show the full model lineage graph.

    Examples:
      aq lineage show
      aq lineage show --format json
    """
    from aquilia.mlops._structures import ModelLineageDAG

    dag = ModelLineageDAG()
    # In a real app the DAG would be loaded from the registry/DB.
    # Here we display whatever is in the current process.
    data = dag.to_dict()

    if fmt == "json":
        click.echo(json.dumps(data, indent=2, default=str))
    else:
        if not data:
            click.echo("No models in lineage graph. Register models first.")
            return
        click.echo(f"{'Model ID':30s} {'Version':10s} {'Parents':30s} Children")
        click.echo("─" * 90)
        for mid, info in data.items():
            parents = ", ".join(info.get("parents", [])) or "—"
            children = ", ".join(info.get("children", [])) or "—"
            click.echo(f"{mid:30s} {info['version']:10s} {parents:30s} {children}")


@lineage_group.command("ancestors")
@click.argument("model_id")
def lineage_ancestors(model_id):
    """
    Show all ancestors (transitive parents) of a model.

    Examples:
      aq lineage ancestors fine-tuned-v2
    """
    from aquilia.mlops._structures import ModelLineageDAG

    dag = ModelLineageDAG()
    ancestors = dag.ancestors(model_id)
    if not ancestors:
        click.echo(f"No ancestors found for '{model_id}' (or model not in graph).")
    else:
        click.echo(f"Ancestors of {model_id}:")
        for a in ancestors:
            click.echo(f"  ← {a}")


@lineage_group.command("descendants")
@click.argument("model_id")
def lineage_descendants(model_id):
    """
    Show all descendants (derived models) of a model.

    Examples:
      aq lineage descendants base-model-v1
    """
    from aquilia.mlops._structures import ModelLineageDAG

    dag = ModelLineageDAG()
    descendants = dag.descendants(model_id)
    if not descendants:
        click.echo(f"No descendants found for '{model_id}' (or model not in graph).")
    else:
        click.echo(f"Descendants of {model_id}:")
        for d in descendants:
            click.echo(f"  → {d}")


@lineage_group.command("path")
@click.argument("from_model")
@click.argument("to_model")
def lineage_path(from_model, to_model):
    """
    Find derivation path between two models.

    Examples:
      aq lineage path base-v1 prod-v3
    """
    from aquilia.mlops._structures import ModelLineageDAG

    dag = ModelLineageDAG()
    path = dag.path(from_model, to_model)
    if path is None:
        click.echo(f"No path found from '{from_model}' to '{to_model}'.")
    else:
        click.echo(" → ".join(path))


# ═══════════════════════════════════════════════════════════════════════════
# aq experiment — A/B experiment management
# ═══════════════════════════════════════════════════════════════════════════

@click.group("experiment")
def experiment_group():
    """A/B experiment management commands."""
    pass


@experiment_group.command("create")
@click.argument("experiment_id")
@click.option("--description", "-d", default="", help="Experiment description")
@click.option("--arm", "-a", multiple=True, help="Arm spec: name:version:weight (e.g. control:v1:0.5)")
def experiment_create(experiment_id, description, arm):
    """
    Create a new A/B experiment.

    Examples:
      aq experiment create latency-test -d "Compare v1 vs v2" \\
        -a control:v1:0.5 -a treatment:v2:0.5
    """
    from aquilia.mlops._structures import ExperimentLedger

    ledger = ExperimentLedger()
    arms = []
    for a in arm:
        parts = a.split(":")
        if len(parts) < 2:
            click.echo(click.style(f"✗ Invalid arm spec: {a} (expected name:version[:weight])", fg="red"))
            sys.exit(1)
        arms.append({
            "name": parts[0],
            "model_version": parts[1],
            "weight": float(parts[2]) if len(parts) > 2 else 0.5,
        })

    exp = ledger.create(experiment_id, description=description, arms=arms)
    click.echo(click.style(f"✓ Experiment created: {experiment_id}", fg="green"))
    click.echo(json.dumps(ledger.summary(experiment_id), indent=2, default=str))


@experiment_group.command("list")
def experiment_list():
    """
    List all experiments.

    Examples:
      aq experiment list
    """
    from aquilia.mlops._structures import ExperimentLedger

    ledger = ExperimentLedger()
    data = ledger.to_dict()
    if not data:
        click.echo("No experiments. Create one with: aq experiment create <id>")
        return

    click.echo(f"{'ID':25s} {'Status':12s} {'Arms':5s} Winner")
    click.echo("─" * 60)
    for eid, info in data.items():
        status = info.get("status", "?")
        n_arms = len(info.get("arms", []))
        winner = info.get("metadata", {}).get("winner", "—")
        click.echo(f"{eid:25s} {status:12s} {n_arms:5d} {winner}")


@experiment_group.command("conclude")
@click.argument("experiment_id")
@click.option("--winner", "-w", default="", help="Winning arm name")
def experiment_conclude(experiment_id, winner):
    """
    Conclude an experiment and optionally declare a winner.

    Examples:
      aq experiment conclude latency-test --winner treatment
    """
    from aquilia.mlops._structures import ExperimentLedger

    ledger = ExperimentLedger()
    exp = ledger.get(experiment_id)
    if not exp:
        click.echo(click.style(f"✗ Experiment '{experiment_id}' not found", fg="red"))
        sys.exit(1)

    ledger.conclude(experiment_id, winner)
    click.echo(click.style(f"✓ Experiment '{experiment_id}' concluded", fg="green"))
    if winner:
        click.echo(f"  Winner: {winner}")


@experiment_group.command("summary")
@click.argument("experiment_id")
def experiment_summary(experiment_id):
    """
    Show detailed experiment summary with per-arm metrics.

    Examples:
      aq experiment summary latency-test
    """
    from aquilia.mlops._structures import ExperimentLedger

    ledger = ExperimentLedger()
    data = ledger.summary(experiment_id)
    if not data:
        click.echo(click.style(f"✗ Experiment '{experiment_id}' not found", fg="red"))
        sys.exit(1)

    click.echo(json.dumps(data, indent=2, default=str))
