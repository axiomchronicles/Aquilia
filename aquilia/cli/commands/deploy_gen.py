"""
Deploy CLI commands — ``aq deploy`` group.

Production-ready deployment file generators for Aquilia workspaces.
Each sub-command generates a specific deployment artefact:

    aq deploy dockerfile   — Dockerfile (production / dev / mlops)
    aq deploy compose      — docker-compose.yml
    aq deploy kubernetes   — Full Kubernetes manifest suite
    aq deploy nginx        — Nginx reverse-proxy configuration
    aq deploy ci           — CI/CD pipeline (GitHub Actions / GitLab CI)
    aq deploy monitoring   — Prometheus + Grafana provisioning
    aq deploy env          — .env.example template
    aq deploy makefile     — Makefile with dev/build/deploy targets
    aq deploy all          — Generate everything at once

All generators introspect the workspace (workspace.py, config/, modules/,
pyproject.toml) to detect enabled components (DB, cache, sessions, auth,
mail, mlops, websockets, effects) and tailor the output accordingly.

Flags:
    --force     Overwrite existing files (default: skip existing)
    --dry-run   Preview what would be generated without writing
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import click

from ..utils.colors import success, error, info, warning, dim


def _get_ctx(workspace_root: Path) -> dict:
    """Introspect the workspace and return a context dict."""
    from ..generators.deployment import WorkspaceIntrospector
    return WorkspaceIntrospector(workspace_root).introspect()


def _write_file(
    path: Path,
    content: str,
    *,
    label: str,
    verbose: bool,
    force: bool = False,
    dry_run: bool = False,
) -> bool:
    """Write content to a file, creating parent directories.

    Returns True if the file was written, False if skipped.
    """
    if path.exists() and not force:
        dim(f"  ⊘ {label} (exists, use --force to overwrite)")
        return False

    if dry_run:
        info(f"  ◎ {label} (dry-run)")
        return True

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    if verbose:
        dim(f"  → {path}")
    success(f"  ✓ {label}")
    return True


# ═══════════════════════════════════════════════════════════════════════════
# Click group
# ═══════════════════════════════════════════════════════════════════════════

@click.group("deploy")
@click.option("--force", "-f", is_flag=True, help="Overwrite existing files")
@click.option("--dry-run", is_flag=True, help="Preview without writing files")
@click.pass_context
def deploy_gen_group(ctx, force: bool, dry_run: bool):
    """Generate production deployment files.

    Introspects your Aquilia workspace and generates Docker, Compose,
    Kubernetes, Nginx, CI/CD, and monitoring configuration files
    tailored to the components you use.

    Flags:
      --force     Overwrite existing files
      --dry-run   Preview what would be generated

    Examples:
      aq deploy dockerfile
      aq deploy compose --monitoring
      aq deploy kubernetes
      aq deploy all
      aq deploy all --force
      aq deploy all --dry-run
    """
    ctx.ensure_object(dict)
    ctx.obj["force"] = force
    ctx.obj["dry_run"] = dry_run


# ═══════════════════════════════════════════════════════════════════════════
# aq deploy dockerfile
# ═══════════════════════════════════════════════════════════════════════════

@deploy_gen_group.command("dockerfile")
@click.option("--dev", "dev_mode", is_flag=True, help="Generate development Dockerfile (with hot-reload)")
@click.option("--mlops", "mlops_mode", is_flag=True, help="Generate MLOps model-serving Dockerfile")
@click.option("--output", "-o", type=click.Path(), default=".", help="Output directory")
@click.pass_context
def deploy_dockerfile(ctx, dev_mode: bool, mlops_mode: bool, output: str):
    """
    Generate production-ready Dockerfiles.

    Creates a multi-stage Dockerfile optimised for Aquilia with
    non-root user, health-checks, tini init, BuildKit cache mounts,
    and artifact compilation.

    Examples:
      aq deploy dockerfile
      aq deploy dockerfile --dev
      aq deploy dockerfile --mlops
      aq deploy dockerfile --dev --mlops   # Generate all variants
      aq deploy -f dockerfile              # Force overwrite
    """
    from ..generators.deployment import DockerfileGenerator

    workspace_root = Path.cwd()
    out = Path(output)
    verbose = ctx.obj.get("verbose", False)
    force = ctx.obj.get("force", False)
    dry_run = ctx.obj.get("dry_run", False)

    try:
        wctx = _get_ctx(workspace_root)
        gen = DockerfileGenerator(wctx)

        if dry_run:
            info(f"🐳 [DRY RUN] Dockerfiles for '{wctx['name']}':")
        else:
            info(f"🐳 Generating Dockerfiles for '{wctx['name']}'...")

        info(f"  📋 Detected: {wctx.get('module_count', 0)} modules, "
             f"db={wctx.get('db_driver', 'none')}, "
             f"Python {wctx.get('python_version', '3.12')}")

        # Always generate production Dockerfile + .dockerignore
        if not dev_mode or mlops_mode:
            _write_file(out / "Dockerfile", gen.generate_dockerfile(),
                        label="Dockerfile (production)", verbose=verbose,
                        force=force, dry_run=dry_run)
            _write_file(out / ".dockerignore", gen.generate_dockerignore(),
                        label=".dockerignore", verbose=verbose,
                        force=force, dry_run=dry_run)

        if dev_mode:
            _write_file(out / "Dockerfile.dev", gen.generate_dockerfile_dev(),
                        label="Dockerfile.dev (development)", verbose=verbose,
                        force=force, dry_run=dry_run)
            if not mlops_mode:
                _write_file(out / ".dockerignore", gen.generate_dockerignore(),
                            label=".dockerignore", verbose=verbose,
                            force=force, dry_run=dry_run)

        if mlops_mode or wctx.get("has_mlops"):
            _write_file(out / "Dockerfile.mlops", gen.generate_dockerfile_mlops(),
                        label="Dockerfile.mlops (model-serving)", verbose=verbose,
                        force=force, dry_run=dry_run)

        info("")
        info("Next steps:")
        info("  docker build -t myapp .")
        info("  docker run -p 8000:8000 myapp")

    except Exception as e:
        error(f"✗ Dockerfile generation failed: {e}")
        sys.exit(1)


# ═══════════════════════════════════════════════════════════════════════════
# aq deploy compose
# ═══════════════════════════════════════════════════════════════════════════

@deploy_gen_group.command("compose")
@click.option("--dev", "dev_mode", is_flag=True, help="Also generate docker-compose.dev.yml")
@click.option("--monitoring", is_flag=True, help="Include Prometheus + Grafana services")
@click.option("--output", "-o", type=click.Path(), default=".", help="Output directory")
@click.pass_context
def deploy_compose(ctx, dev_mode: bool, monitoring: bool, output: str):
    """
    Generate docker-compose.yml for the workspace.

    Auto-detects services: PostgreSQL, MySQL, Redis, MLOps model server,
    Nginx, monitoring, and mail based on your workspace configuration.
    Uses compose profiles for optional services (mlops, monitoring, dev).

    Examples:
      aq deploy compose
      aq deploy compose --monitoring
      aq deploy compose --dev
      aq deploy -f compose   # Force overwrite
    """
    from ..generators.deployment import ComposeGenerator

    workspace_root = Path.cwd()
    out = Path(output)
    verbose = ctx.obj.get("verbose", False)
    force = ctx.obj.get("force", False)
    dry_run = ctx.obj.get("dry_run", False)

    try:
        wctx = _get_ctx(workspace_root)
        gen = ComposeGenerator(wctx)

        if dry_run:
            info(f"🐳 [DRY RUN] Docker Compose for '{wctx['name']}':")
        else:
            info(f"🐳 Generating Docker Compose for '{wctx['name']}'...")

        _write_file(out / "docker-compose.yml",
                     gen.generate_compose(include_monitoring=monitoring),
                     label="docker-compose.yml", verbose=verbose,
                     force=force, dry_run=dry_run)

        if dev_mode:
            _write_file(out / "docker-compose.dev.yml",
                         gen.generate_compose_dev(),
                         label="docker-compose.dev.yml", verbose=verbose,
                         force=force, dry_run=dry_run)

        info("")
        info("Next steps:")
        info("  docker compose up -d")
        info("  docker compose --profile monitoring up -d")
        info("  docker compose logs -f app")

    except Exception as e:
        error(f"✗ Compose generation failed: {e}")
        sys.exit(1)


# ═══════════════════════════════════════════════════════════════════════════
# aq deploy kubernetes
# ═══════════════════════════════════════════════════════════════════════════

@deploy_gen_group.command("kubernetes")
@click.option("--output", "-o", type=click.Path(), default="k8s", help="Output directory")
@click.option("--mlops", is_flag=True, help="Force include MLOps manifests")
@click.pass_context
def deploy_kubernetes(ctx, output: str, mlops: bool):
    """
    Generate production Kubernetes manifests.

    Generates namespace, deployment, service, ingress, HPA, PDB,
    network policy, configmap, secret, service account, PVC,
    CronJob for maintenance, and init containers for DB readiness.
    Includes MLOps manifests if mlops components are detected.

    Examples:
      aq deploy kubernetes
      aq deploy kubernetes -o deploy/k8s
      aq deploy kubernetes --mlops
    """
    from ..generators.deployment import KubernetesGenerator

    workspace_root = Path.cwd()
    out = Path(output)
    verbose = ctx.obj.get("verbose", False)
    force = ctx.obj.get("force", False)
    dry_run = ctx.obj.get("dry_run", False)

    try:
        wctx = _get_ctx(workspace_root)
        if mlops:
            wctx["has_mlops"] = True

        gen = KubernetesGenerator(wctx)

        if dry_run:
            info(f"☸  [DRY RUN] Kubernetes manifests for '{wctx['name']}':")
        else:
            info(f"☸  Generating Kubernetes manifests for '{wctx['name']}'...")

        manifests = gen.generate_all()
        for filename, content in manifests.items():
            _write_file(out / filename, content,
                         label=filename, verbose=verbose,
                         force=force, dry_run=dry_run)

        # Generate kustomization.yaml
        kustomize_resources = "\n".join(f"  - {f}" for f in sorted(manifests.keys()))
        kustomize_content = (
            f"# Kustomize configuration for {wctx['name']}\n"
            f"# Generated by: aq deploy kubernetes\n\n"
            f"apiVersion: kustomize.config.k8s.io/v1beta1\n"
            f"kind: Kustomization\n\n"
            f"namespace: {wctx['name']}\n\n"
            f"commonLabels:\n"
            f"  app.kubernetes.io/managed-by: aquilia-cli\n\n"
            f"resources:\n{kustomize_resources}\n"
        )
        _write_file(out / "kustomization.yaml", kustomize_content,
                     label="kustomization.yaml", verbose=verbose,
                     force=force, dry_run=dry_run)

        info("")
        info(f"  📊 Generated {len(manifests)} manifests + kustomization.yaml")
        info("")
        info("Next steps:")
        info(f"  kubectl apply -k {output}/")
        info("  # Or with kustomize: kustomize build k8s/ | kubectl apply -f -")

    except Exception as e:
        error(f"✗ Kubernetes generation failed: {e}")
        sys.exit(1)


# ═══════════════════════════════════════════════════════════════════════════
# aq deploy nginx
# ═══════════════════════════════════════════════════════════════════════════

@deploy_gen_group.command("nginx")
@click.option("--output", "-o", type=click.Path(), default="deploy/nginx", help="Output directory")
@click.pass_context
def deploy_nginx(ctx, output: str):
    """
    Generate Nginx reverse-proxy configuration.

    Includes rate-limiting, security headers (HSTS, CSP, XSS), gzip,
    WebSocket upgrade support, upstream keepalive, and MLOps proxy
    if detected. HTTPS block included (commented) with modern TLS config.

    Examples:
      aq deploy nginx
      aq deploy nginx -o config/nginx
    """
    from ..generators.deployment import NginxGenerator

    workspace_root = Path.cwd()
    out = Path(output)
    verbose = ctx.obj.get("verbose", False)
    force = ctx.obj.get("force", False)
    dry_run = ctx.obj.get("dry_run", False)

    try:
        wctx = _get_ctx(workspace_root)
        gen = NginxGenerator(wctx)

        if dry_run:
            info(f"🌐 [DRY RUN] Nginx config for '{wctx['name']}':")
        else:
            info(f"🌐 Generating Nginx config for '{wctx['name']}'...")

        _write_file(out / "nginx.conf", gen.generate_nginx_conf(),
                     label="nginx.conf", verbose=verbose,
                     force=force, dry_run=dry_run)

        # Create ssl directory placeholder
        if not dry_run:
            ssl_dir = out / "ssl"
            ssl_dir.mkdir(parents=True, exist_ok=True)
            _write_file(ssl_dir / ".gitkeep", "",
                         label="ssl/.gitkeep (placeholder)", verbose=verbose,
                         force=force, dry_run=dry_run)

        info("")
        info("Next steps:")
        info("  1. Place TLS certificates in deploy/nginx/ssl/")
        info("  2. Uncomment HTTPS block in nginx.conf")

    except Exception as e:
        error(f"✗ Nginx generation failed: {e}")
        sys.exit(1)


# ═══════════════════════════════════════════════════════════════════════════
# aq deploy ci
# ═══════════════════════════════════════════════════════════════════════════

@deploy_gen_group.command("ci")
@click.option("--provider", type=click.Choice(["github", "gitlab"]), default="github",
              help="CI provider")
@click.option("--output", "-o", type=click.Path(), default=None, help="Output directory")
@click.pass_context
def deploy_ci(ctx, provider: str, output: Optional[str]):
    """
    Generate CI/CD pipeline configuration.

    Creates a CI/CD workflow with lint, test, security scan, build,
    and deploy stages. Includes Trivy container scanning, dependency
    auditing, and Aquilia-specific validation steps.

    Supported providers:
      --provider=github   GitHub Actions (default)
      --provider=gitlab   GitLab CI/CD

    Examples:
      aq deploy ci
      aq deploy ci --provider=github
      aq deploy ci --provider=gitlab
    """
    from ..generators.deployment import CIGenerator

    workspace_root = Path.cwd()
    verbose = ctx.obj.get("verbose", False)
    force = ctx.obj.get("force", False)
    dry_run = ctx.obj.get("dry_run", False)

    try:
        wctx = _get_ctx(workspace_root)
        gen = CIGenerator(wctx)

        if dry_run:
            info(f"⚙  [DRY RUN] CI/CD pipeline for '{wctx['name']}' ({provider}):")
        else:
            info(f"⚙  Generating CI/CD pipeline for '{wctx['name']}' ({provider})...")

        if provider == "github":
            out_dir = Path(output) if output else workspace_root / ".github" / "workflows"
            _write_file(out_dir / "ci.yml", gen.generate_github_actions(),
                         label=".github/workflows/ci.yml", verbose=verbose,
                         force=force, dry_run=dry_run)
        elif provider == "gitlab":
            out_dir = Path(output) if output else workspace_root
            _write_file(out_dir / ".gitlab-ci.yml", gen.generate_gitlab_ci(),
                         label=".gitlab-ci.yml", verbose=verbose,
                         force=force, dry_run=dry_run)

        info("")
        info("Next steps:")
        info("  1. Review the generated workflow")
        info("  2. Configure secrets in repository settings")
        info("  3. Push to trigger CI")

    except Exception as e:
        error(f"✗ CI generation failed: {e}")
        sys.exit(1)


# ═══════════════════════════════════════════════════════════════════════════
# aq deploy monitoring
# ═══════════════════════════════════════════════════════════════════════════

@deploy_gen_group.command("monitoring")
@click.option("--output", "-o", type=click.Path(), default="deploy", help="Output base directory")
@click.pass_context
def deploy_monitoring(ctx, output: str):
    """
    Generate monitoring configuration (Prometheus + Grafana).

    Creates Prometheus scrape config and Grafana provisioning files
    for Aquilia app and MLOps model server metrics.

    Prometheus scrape targets are auto-configured based on detected
    modules (app metrics, model-server, Redis, Postgres exporters).

    Examples:
      aq deploy monitoring
      aq deploy monitoring -o infra/
      aq deploy monitoring --force
    """
    from ..generators.deployment import PrometheusGenerator, GrafanaGenerator

    workspace_root = Path.cwd()
    out = Path(output)
    verbose = ctx.obj.get("verbose", False)
    force = ctx.obj.get("force", False)
    dry_run = ctx.obj.get("dry_run", False)

    try:
        wctx = _get_ctx(workspace_root)

        if dry_run:
            info(f"📊  [DRY RUN] Monitoring config for '{wctx['name']}':")
        else:
            info(f"📊  Generating monitoring config for '{wctx['name']}'...")

        prom_gen = PrometheusGenerator(wctx)
        _write_file(out / "prometheus" / "prometheus.yml",
                     prom_gen.generate_prometheus_yml(),
                     label="prometheus/prometheus.yml", verbose=verbose,
                     force=force, dry_run=dry_run)

        graf_gen = GrafanaGenerator(wctx)
        _write_file(out / "grafana" / "provisioning" / "datasources" / "datasource.yml",
                     graf_gen.generate_datasource(),
                     label="grafana/provisioning/datasources/datasource.yml", verbose=verbose,
                     force=force, dry_run=dry_run)
        _write_file(out / "grafana" / "provisioning" / "dashboards" / "dashboards.yml",
                     graf_gen.generate_dashboard_provisioning(),
                     label="grafana/provisioning/dashboards/dashboards.yml", verbose=verbose,
                     force=force, dry_run=dry_run)

        info("")
        info("Next steps:")
        info("  aq deploy compose --monitoring")
        info("  docker compose up -d prometheus grafana")
        info("  Open Grafana at http://localhost:3000 (admin/admin)")

    except Exception as e:
        error(f"✗ Monitoring generation failed: {e}")
        sys.exit(1)


# ═══════════════════════════════════════════════════════════════════════════
# aq deploy env
# ═══════════════════════════════════════════════════════════════════════════

@deploy_gen_group.command("env")
@click.option("--output", "-o", type=click.Path(), default=".", help="Output directory")
@click.pass_context
def deploy_env(ctx, output: str):
    """
    Generate .env.example template with all Aquilia settings.

    Scans the workspace for enabled components and generates
    a comprehensive environment variable template. Includes
    db-driver-aware DATABASE_URL defaults, telemetry, CORS,
    and monitoring sections when relevant.

    Examples:
      aq deploy env
      aq deploy env --force
    """
    from ..generators.deployment import EnvGenerator

    workspace_root = Path.cwd()
    out = Path(output)
    verbose = ctx.obj.get("verbose", False)
    force = ctx.obj.get("force", False)
    dry_run = ctx.obj.get("dry_run", False)

    try:
        wctx = _get_ctx(workspace_root)
        gen = EnvGenerator(wctx)

        if dry_run:
            info(f"📝  [DRY RUN] .env.example for '{wctx['name']}':")
        else:
            info(f"📝  Generating .env.example for '{wctx['name']}'...")

        _write_file(out / ".env.example", gen.generate_env_example(),
                     label=".env.example", verbose=verbose,
                     force=force, dry_run=dry_run)

        db = wctx.get("db_driver", "sqlite")
        info("")
        info(f"  DB driver detected: {db}")
        info("")
        info("Next steps:")
        info("  cp .env.example .env")
        info("  # Fill in real secrets — never commit .env")

    except Exception as e:
        error(f"✗ Env generation failed: {e}")
        sys.exit(1)


# ═══════════════════════════════════════════════════════════════════════════
# aq deploy all
# ═══════════════════════════════════════════════════════════════════════════

@deploy_gen_group.command("all")
@click.option("--output", "-o", type=click.Path(), default=".", help="Output base directory")
@click.option("--monitoring", is_flag=True, default=True, help="Include monitoring (default: yes)")
@click.option("--ci-provider", type=click.Choice(["github", "gitlab", "both"]),
              default="github", help="CI/CD provider")
@click.pass_context
def deploy_all(ctx, output: str, monitoring: bool, ci_provider: str):
    """
    Generate ALL deployment files at once.

    Creates Dockerfile, docker-compose.yml, Kubernetes manifests,
    Nginx config, CI/CD pipeline(s), Makefile, monitoring, and
    .env template.  Respects --force and --dry-run flags.

    Examples:
      aq deploy all
      aq deploy all -o deploy/
      aq deploy all --ci-provider=both --force
    """
    from ..generators.deployment import (
        DockerfileGenerator,
        ComposeGenerator,
        KubernetesGenerator,
        NginxGenerator,
        CIGenerator,
        PrometheusGenerator,
        GrafanaGenerator,
        EnvGenerator,
        MakefileGenerator,
    )

    workspace_root = Path.cwd()
    out = Path(output)
    verbose = ctx.obj.get("verbose", False)
    force = ctx.obj.get("force", False)
    dry_run = ctx.obj.get("dry_run", False)
    written = 0  # track files written

    try:
        wctx = _get_ctx(workspace_root)
        name = wctx["name"]

        if dry_run:
            info(f"🚀  [DRY RUN] Full deployment suite for '{name}':\n")
        else:
            info(f"🚀  Generating full deployment suite for '{name}'...\n")

        # ── Dockerfiles ──
        info("── Docker ──")
        docker_gen = DockerfileGenerator(wctx)
        if _write_file(out / "Dockerfile", docker_gen.generate_dockerfile(),
                       label="Dockerfile", verbose=verbose,
                       force=force, dry_run=dry_run):
            written += 1
        if _write_file(out / "Dockerfile.dev", docker_gen.generate_dockerfile_dev(),
                       label="Dockerfile.dev", verbose=verbose,
                       force=force, dry_run=dry_run):
            written += 1
        if _write_file(out / ".dockerignore", docker_gen.generate_dockerignore(),
                       label=".dockerignore", verbose=verbose,
                       force=force, dry_run=dry_run):
            written += 1
        if wctx.get("has_mlops"):
            if _write_file(out / "Dockerfile.mlops", docker_gen.generate_dockerfile_mlops(),
                           label="Dockerfile.mlops", verbose=verbose,
                           force=force, dry_run=dry_run):
                written += 1

        # ── Compose ──
        info("\n── Docker Compose ──")
        compose_gen = ComposeGenerator(wctx)
        if _write_file(out / "docker-compose.yml",
                       compose_gen.generate_compose(include_monitoring=monitoring),
                       label="docker-compose.yml", verbose=verbose,
                       force=force, dry_run=dry_run):
            written += 1
        if _write_file(out / "docker-compose.dev.yml",
                       compose_gen.generate_compose_dev(),
                       label="docker-compose.dev.yml", verbose=verbose,
                       force=force, dry_run=dry_run):
            written += 1

        # ── Kubernetes ──
        info("\n── Kubernetes ──")
        k8s_gen = KubernetesGenerator(wctx)
        manifests = k8s_gen.generate_all()
        for filename, content in manifests.items():
            if _write_file(out / "k8s" / filename, content,
                           label=f"k8s/{filename}", verbose=verbose,
                           force=force, dry_run=dry_run):
                written += 1

        kustomize_resources = "\n".join(f"  - {f}" for f in sorted(manifests.keys()))
        common_labels = (
            f"commonLabels:\n"
            f"  app.kubernetes.io/name: {name}\n"
            f"  app.kubernetes.io/managed-by: aquilia-cli\n"
        )
        if _write_file(out / "k8s" / "kustomization.yaml",
                       f"apiVersion: kustomize.config.k8s.io/v1beta1\n"
                       f"kind: Kustomization\nnamespace: {name}\n\n"
                       f"{common_labels}\n"
                       f"resources:\n{kustomize_resources}\n",
                       label="k8s/kustomization.yaml", verbose=verbose,
                       force=force, dry_run=dry_run):
            written += 1

        # ── Nginx ──
        info("\n── Nginx ──")
        nginx_gen = NginxGenerator(wctx)
        if _write_file(out / "deploy" / "nginx" / "nginx.conf",
                       nginx_gen.generate_nginx_conf(),
                       label="deploy/nginx/nginx.conf", verbose=verbose,
                       force=force, dry_run=dry_run):
            written += 1
        if not dry_run:
            (out / "deploy" / "nginx" / "ssl").mkdir(parents=True, exist_ok=True)
        if _write_file(out / "deploy" / "nginx" / "ssl" / ".gitkeep", "",
                       label="deploy/nginx/ssl/.gitkeep", verbose=verbose,
                       force=force, dry_run=dry_run):
            written += 1

        # ── CI/CD ──
        info("\n── CI/CD ──")
        ci_gen = CIGenerator(wctx)
        if ci_provider in ("github", "both"):
            if _write_file(out / ".github" / "workflows" / "ci.yml",
                           ci_gen.generate_github_actions(),
                           label=".github/workflows/ci.yml", verbose=verbose,
                           force=force, dry_run=dry_run):
                written += 1
        if ci_provider in ("gitlab", "both"):
            if _write_file(out / ".gitlab-ci.yml",
                           ci_gen.generate_gitlab_ci(),
                           label=".gitlab-ci.yml", verbose=verbose,
                           force=force, dry_run=dry_run):
                written += 1

        # ── Monitoring ──
        if monitoring:
            info("\n── Monitoring ──")
            prom_gen = PrometheusGenerator(wctx)
            if _write_file(out / "deploy" / "prometheus" / "prometheus.yml",
                           prom_gen.generate_prometheus_yml(),
                           label="deploy/prometheus/prometheus.yml", verbose=verbose,
                           force=force, dry_run=dry_run):
                written += 1
            graf_gen = GrafanaGenerator(wctx)
            if _write_file(out / "deploy" / "grafana" / "provisioning" / "datasources" / "datasource.yml",
                           graf_gen.generate_datasource(),
                           label="deploy/grafana/provisioning/datasources/datasource.yml",
                           verbose=verbose, force=force, dry_run=dry_run):
                written += 1
            if _write_file(out / "deploy" / "grafana" / "provisioning" / "dashboards" / "dashboards.yml",
                           graf_gen.generate_dashboard_provisioning(),
                           label="deploy/grafana/provisioning/dashboards/dashboards.yml",
                           verbose=verbose, force=force, dry_run=dry_run):
                written += 1

        # ── Env ──
        info("\n── Environment ──")
        env_gen = EnvGenerator(wctx)
        if _write_file(out / ".env.example", env_gen.generate_env_example(),
                       label=".env.example", verbose=verbose,
                       force=force, dry_run=dry_run):
            written += 1

        # ── Makefile ──
        info("\n── Makefile ──")
        mk_gen = MakefileGenerator(wctx)
        if _write_file(out / "Makefile", mk_gen.generate_makefile(),
                       label="Makefile", verbose=verbose,
                       force=force, dry_run=dry_run):
            written += 1

        # ── Summary ──
        info("")
        if dry_run:
            info(f"  {written} file(s) would be generated")
        else:
            success(f"✓ {written} file(s) generated for '{name}'")
        info("")
        info("Quick start:")
        info("  1. cp .env.example .env && edit .env")
        info("  2. make docker-up                (Docker Compose)")
        info("  3. make k8s-apply                (Kubernetes)")
        info("  4. make help                     (see all targets)")
        info("")
        info("Generated structure:")
        dim(f"  Dockerfile               — Production (multi-stage, BuildKit)")
        dim(f"  Dockerfile.dev           — Development (hot-reload)")
        dim(f"  .dockerignore            — Build context exclusions")
        if wctx.get("has_mlops"):
            dim(f"  Dockerfile.mlops         — MLOps model server")
        dim(f"  docker-compose.yml       — Full service stack (profiles)")
        dim(f"  docker-compose.dev.yml   — Dev override")
        dim(f"  k8s/                     — Kubernetes manifests ({len(manifests)} files)")
        dim(f"  deploy/nginx/            — Nginx reverse-proxy (TLS-ready)")
        if monitoring:
            dim(f"  deploy/prometheus/       — Prometheus config")
            dim(f"  deploy/grafana/          — Grafana provisioning")
        if ci_provider in ("github", "both"):
            dim(f"  .github/workflows/       — GitHub Actions pipeline")
        if ci_provider in ("gitlab", "both"):
            dim(f"  .gitlab-ci.yml           — GitLab CI/CD pipeline")
        dim(f"  .env.example             — Environment template")
        dim(f"  Makefile                 — Dev/deploy task runner")

    except Exception as e:
        error(f"✗ Full deployment generation failed: {e}")
        sys.exit(1)


# ═══════════════════════════════════════════════════════════════════════════
# aq deploy makefile
# ═══════════════════════════════════════════════════════════════════════════

@deploy_gen_group.command("makefile")
@click.option("--output", "-o", type=click.Path(), default=".", help="Output directory")
@click.pass_context
def deploy_makefile(ctx, output: str):
    """
    Generate a self-documenting Makefile for dev & ops tasks.

    Includes targets for running, testing, linting, Docker build/up/down,
    Kubernetes apply/delete, database migrations, and deployment file
    generation.  Run `make help` to see all targets.

    Examples:
      aq deploy makefile
      aq deploy makefile --force
    """
    from ..generators.deployment import MakefileGenerator

    workspace_root = Path.cwd()
    out = Path(output)
    verbose = ctx.obj.get("verbose", False)
    force = ctx.obj.get("force", False)
    dry_run = ctx.obj.get("dry_run", False)

    try:
        wctx = _get_ctx(workspace_root)

        if dry_run:
            info(f"🛠  [DRY RUN] Makefile for '{wctx['name']}':")
        else:
            info(f"🛠  Generating Makefile for '{wctx['name']}'...")

        gen = MakefileGenerator(wctx)
        _write_file(out / "Makefile", gen.generate_makefile(),
                     label="Makefile", verbose=verbose,
                     force=force, dry_run=dry_run)

        info("")
        info("Next steps:")
        info("  make help          # see all available targets")
        info("  make dev           # start dev server")
        info("  make docker-up     # bring up compose stack")

    except Exception as e:
        error(f"✗ Makefile generation failed: {e}")
        sys.exit(1)
