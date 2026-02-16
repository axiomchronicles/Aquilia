"""
Aquilia Deployment Generators — Production-ready Docker, Compose, Kubernetes,
Nginx, CI/CD, and monitoring file generators.

Deeply integrated with the Aquilia ecosystem:
- Discovery: scans workspace for modules, controllers, services
- Config: reads workspace.py, config/*.yaml, pyproject.toml
- Artifacts: leverages artifact system for build fingerprints
- Trace: integrates with .aquilia/ diagnostics directory
- Faults: generates health-check endpoints compatible with fault domains
- MLOps: generates separate model-serving containers & k8s manifests
- Sessions: configures Redis/store backends in compose
- Cache: provisions cache backends in deployment
- Effects: maps effect providers to infrastructure services
- Serializers: configures API serialization layers
- Auth: generates secrets management in k8s
- Migrations: init containers & CronJobs for database migrations
- Security: trivy scanning in CI, network policies, pod security

Usage::

    from aquilia.cli.generators.deployment import (
        DockerfileGenerator,
        ComposeGenerator,
        KubernetesGenerator,
        NginxGenerator,
        CIGenerator,
        MakefileGenerator,
    )
"""

from __future__ import annotations

import textwrap
import re
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone


# ═══════════════════════════════════════════════════════════════════════════
# Workspace Introspection
# ═══════════════════════════════════════════════════════════════════════════

class WorkspaceIntrospector:
    """
    Introspects an Aquilia workspace to discover configuration needed
    for production deployment file generation.

    Reads workspace.py, config/*.yaml, pyproject.toml, module manifests,
    and detects ecosystem components (cache, sessions, db, mlops, sockets,
    mail, auth, openapi, templates, security, etc.).

    Provides:
    - Deep workspace.py regex parsing for all builder methods
    - pyproject.toml parsing for Python version & dependency detection
    - Nested YAML config parsing (server.port, server.workers, etc.)
    - Module manifest scanning (controllers, services, faults count)
    - Intelligent worker/replica sizing based on module complexity
    - Database driver detection (postgres, mysql, sqlite)
    """

    def __init__(self, workspace_root: Path):
        self.root = workspace_root
        self._cache: Optional[Dict[str, Any]] = None

    def introspect(self) -> Dict[str, Any]:
        """Return a full introspection dictionary."""
        if self._cache is not None:
            return self._cache

        result: Dict[str, Any] = {
            "name": self.root.name,
            "version": "0.1.0",
            "python_version": "3.12",
            "port": 8000,
            "host": "0.0.0.0",
            "workers": 4,
            "modules": [],
            "module_count": 0,
            "controller_count": 0,
            "service_count": 0,
            "has_db": False,
            "db_url": "",
            "db_driver": "sqlite",
            "has_cache": False,
            "cache_backend": "memory",
            "has_sessions": False,
            "session_store": "memory",
            "has_websockets": False,
            "has_mlops": False,
            "has_mail": False,
            "has_auth": False,
            "has_templates": False,
            "has_static": False,
            "has_migrations": False,
            "has_openapi": False,
            "has_effects": False,
            "has_faults": False,
            "cors_enabled": False,
            "csrf_protection": False,
            "helmet_enabled": False,
            "rate_limiting": False,
            "tracing_enabled": False,
            "metrics_enabled": False,
            "logging_enabled": False,
            # Dependency info (from pyproject.toml)
            "has_pyproject": False,
            "dependencies": [],
            "has_requirements_txt": False,
            # Deployment-relevant paths
            "has_dockerfile": False,
            "has_compose": False,
            "has_k8s": False,
            # Build metadata
            "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        }

        # ── Parse pyproject.toml for Python version & deps ──
        pyproject_file = self.root / "pyproject.toml"
        if pyproject_file.exists():
            result["has_pyproject"] = True
            result.update(self._parse_pyproject(pyproject_file.read_text()))

        # ── Parse workspace.py ──
        workspace_file = self.root / "workspace.py"
        if workspace_file.exists():
            content = workspace_file.read_text()
            result.update(self._parse_workspace(content))

        # ── Parse config/prod.yaml (or config/base.yaml) for production settings ──
        for cfg_name in ("prod.yaml", "production.yaml", "base.yaml"):
            cfg_path = self.root / "config" / cfg_name
            if cfg_path.exists():
                result.update(self._parse_yaml_config(cfg_path.read_text()))
                break

        # ── Detect modules & count controllers/services ──
        modules_dir = self.root / "modules"
        if modules_dir.exists():
            modules = []
            total_controllers = 0
            total_services = 0
            for d in sorted(modules_dir.iterdir()):
                if d.is_dir() and not d.name.startswith("_"):
                    modules.append(d.name)
                    # Count controllers and services in module
                    ctrl_file = d / "controllers.py"
                    svc_file = d / "services.py"
                    if ctrl_file.exists():
                        ctrl_content = ctrl_file.read_text()
                        total_controllers += len(re.findall(
                            r'^class\s+\w+(?:Controller|Resource|View)\b',
                            ctrl_content, re.MULTILINE,
                        ))
                    if svc_file.exists():
                        svc_content = svc_file.read_text()
                        total_services += len(re.findall(
                            r'^class\s+\w+(?:Service|Repository|Provider)\b',
                            svc_content, re.MULTILINE,
                        ))
            result["modules"] = modules
            result["module_count"] = len(modules)
            result["controller_count"] = total_controllers
            result["service_count"] = total_services

        # ── Detect ecosystem from filesystem ──
        result["has_migrations"] = (self.root / "migrations").exists()
        result["has_static"] = (
            (self.root / "static").exists()
            or result.get("has_static", False)
        )
        result["has_requirements_txt"] = (self.root / "requirements.txt").exists()
        result["has_dockerfile"] = (self.root / "Dockerfile").exists()
        result["has_compose"] = (self.root / "docker-compose.yml").exists()
        result["has_k8s"] = (self.root / "k8s").exists()

        # ── Intelligent worker sizing ──
        if result["workers"] <= 1 and result["module_count"] > 0:
            # Heuristic: 2 workers base + 1 per 4 modules, capped at 8
            result["workers"] = min(8, 2 + result["module_count"] // 4)

        # ── Detect DB driver from URL ──
        db_url = result.get("db_url", "")
        if db_url:
            result["db_driver"] = self._detect_db_driver(db_url)

        self._cache = result
        return result

    @staticmethod
    def _detect_db_driver(db_url: str) -> str:
        """Detect database driver from connection URL."""
        url_lower = db_url.lower()
        if "postgres" in url_lower:
            return "postgres"
        elif "mysql" in url_lower or "mariadb" in url_lower:
            return "mysql"
        elif "sqlite" in url_lower:
            return "sqlite"
        elif "mssql" in url_lower or "sqlserver" in url_lower:
            return "mssql"
        return "sqlite"

    def _parse_pyproject(self, content: str) -> Dict[str, Any]:
        """Parse pyproject.toml for Python version, project name, and deps."""
        data: Dict[str, Any] = {}

        # Project name
        m = re.search(r'^name\s*=\s*"([^"]+)"', content, re.MULTILINE)
        if m:
            data["project_name"] = m.group(1)

        # Project version
        m = re.search(r'^version\s*=\s*"([^"]+)"', content, re.MULTILINE)
        if m:
            data["version"] = m.group(1)

        # Python version requirement → extract min version for Dockerfile
        m = re.search(r'requires-python\s*=\s*">=(\d+\.\d+)"', content)
        if m:
            # Use the minimum required version for broadest compat
            min_py = m.group(1)
            # But prefer 3.12 if min is lower (for Docker image stability)
            major, minor = min_py.split(".")
            if int(minor) < 12:
                data["python_version"] = "3.12"
            else:
                data["python_version"] = min_py

        # Detect dependencies for service provisioning
        deps: List[str] = []
        in_deps = False
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("dependencies") and "=" in stripped:
                in_deps = True
                continue
            if in_deps:
                if stripped == "]":
                    in_deps = False
                    continue
                m = re.match(r'"([a-zA-Z0-9_-]+)', stripped)
                if m:
                    deps.append(m.group(1).lower())
        data["dependencies"] = deps

        # Detect optional dependency groups
        if "mlops" in content.lower() and "[" in content:
            data["has_mlops_deps"] = True

        return data

    def _parse_workspace(self, content: str) -> Dict[str, Any]:
        """Parse workspace.py for deployment-relevant configuration."""
        data: Dict[str, Any] = {}

        # Name
        m = re.search(r'Workspace\(\s*name="([^"]+)"', content)
        if m:
            data["name"] = m.group(1)

        # Version
        m = re.search(r'version="([^"]+)"', content)
        if m:
            data["version"] = m.group(1)

        # Database
        if ".database(" in content:
            data["has_db"] = True
            m = re.search(r'\.database\([^)]*url="([^"]+)"', content)
            if m:
                data["db_url"] = m.group(1)

        # Sessions
        if ".sessions(" in content:
            data["has_sessions"] = True
            if 'store_name="redis"' in content or 'store="redis"' in content:
                data["session_store"] = "redis"
            elif 'store_name="memory"' in content or 'store="memory"' in content:
                data["session_store"] = "memory"

        # Cache
        if "Integration.cache" in content or "cache" in content.lower():
            if "redis" in content.lower():
                data["has_cache"] = True
                data["cache_backend"] = "redis"

        # WebSockets
        if "register_sockets" in content or "AquilaSockets" in content:
            data["has_websockets"] = True

        # Mail
        if "Integration.mail" in content or "AquilaMail" in content:
            data["has_mail"] = True

        # Auth
        if "Integration.auth" in content or "AquilAuth" in content:
            data["has_auth"] = True

        # Templates
        if "Integration.templates" in content:
            data["has_templates"] = True

        # Static files
        if "Integration.static_files" in content:
            data["has_static"] = True

        # OpenAPI
        if "Integration.openapi" in content:
            data["has_openapi"] = True

        # Faults
        if "Integration.fault_handling" in content:
            data["has_faults"] = True

        # Effects
        if "Integration.effects" in content or "Effect(" in content:
            data["has_effects"] = True

        # Security — parse each flag
        sec_match = re.search(
            r'\.security\((.*?)\)', content, re.DOTALL,
        )
        if sec_match:
            sec_block = sec_match.group(1)
            if "cors_enabled=True" in sec_block:
                data["cors_enabled"] = True
            if "csrf_protection=True" in sec_block:
                data["csrf_protection"] = True
            if "helmet_enabled=True" in sec_block:
                data["helmet_enabled"] = True
            if "rate_limiting=True" in sec_block:
                data["rate_limiting"] = True

        # Fallback — global flag detection
        if "cors_enabled=True" in content:
            data["cors_enabled"] = True
        if "rate_limiting=True" in content:
            data["rate_limiting"] = True

        # Telemetry — parse each flag
        tel_match = re.search(
            r'\.telemetry\((.*?)\)', content, re.DOTALL,
        )
        if tel_match:
            tel_block = tel_match.group(1)
            if "tracing_enabled=True" in tel_block:
                data["tracing_enabled"] = True
            if "metrics_enabled=True" in tel_block:
                data["metrics_enabled"] = True
            if "logging_enabled=True" in tel_block:
                data["logging_enabled"] = True

        # Fallback — global flag detection
        if "tracing_enabled=True" in content:
            data["tracing_enabled"] = True
        if "metrics_enabled=True" in content:
            data["metrics_enabled"] = True

        # MLOps — check for mlops module or imports
        if "mlops" in content.lower():
            data["has_mlops"] = True

        return data

    def _parse_yaml_config(self, content: str) -> Dict[str, Any]:
        """
        Parse YAML config for server settings.

        Supports nested structure like:
            server:
              port: 8000
              workers: 4
        as well as flat keys.
        """
        data: Dict[str, Any] = {}
        in_server_block = False

        for line in content.splitlines():
            raw = line
            stripped = line.strip()
            if stripped.startswith("#") or not stripped:
                continue

            # Detect top-level `server:` block
            if raw.startswith("server:") or raw.startswith("server :"):
                in_server_block = True
                continue

            # If we're in a server block and the line is indented, parse it
            if in_server_block:
                if raw[0] not in (" ", "\t"):
                    # Left-aligned line means we've exited the server block
                    in_server_block = False
                else:
                    if ":" in stripped:
                        key, _, value = stripped.partition(":")
                        key = key.strip()
                        value = value.strip()
                        if key == "port" and value.isdigit():
                            data["port"] = int(value)
                        elif key == "host":
                            data["host"] = value.strip('"').strip("'")
                        elif key == "workers" and value.isdigit():
                            data["workers"] = int(value)
                        elif key == "mode":
                            data["mode"] = value.strip('"').strip("'")
                    continue

            # Flat key fallback
            if ":" in stripped:
                key, _, value = stripped.partition(":")
                key = key.strip()
                value = value.strip()
                if key == "port" and value.isdigit():
                    data["port"] = int(value)
                elif key == "host":
                    data["host"] = value.strip('"').strip("'")
                elif key == "workers" and value.isdigit():
                    data["workers"] = int(value)

        return data


# ═══════════════════════════════════════════════════════════════════════════
# Dockerfile Generator
# ═══════════════════════════════════════════════════════════════════════════

class DockerfileGenerator:
    """
    Generates production-ready, multi-stage Dockerfile for Aquilia workspaces.

    Features:
    - Multi-stage build (builder → production)
    - Non-root user security
    - Health-check integration with Aquilia fault system
    - .dockerignore generation
    - Optimised layer caching (deps first, code second)
    - Artifact compilation step
    - Database migration init step (when has_migrations)
    - ARG-based Python version for build-time override
    - Support for MLOps GPU variant
    - BuildKit cache mounts for pip
    """

    def __init__(self, ctx: Dict[str, Any]):
        self.ctx = ctx

    def generate_dockerfile(self) -> str:
        """Generate production Dockerfile."""
        name = self.ctx["name"]
        port = self.ctx.get("port", 8000)
        workers = self.ctx.get("workers", 4)
        python_version = self.ctx.get("python_version", "3.12")
        has_migrations = self.ctx.get("has_migrations", False)
        has_db = self.ctx.get("has_db", False)
        db_driver = self.ctx.get("db_driver", "sqlite")

        # Build extra system deps based on database driver
        extra_build_deps = []
        extra_runtime_deps = []
        if has_db and db_driver == "postgres":
            extra_build_deps.append("libpq-dev")
            extra_runtime_deps.append("libpq5")
        elif has_db and db_driver == "mysql":
            extra_build_deps.append("default-libmysqlclient-dev")
            extra_runtime_deps.append("default-mysql-client")

        build_deps_str = " \\\n                    ".join(
            ["build-essential", "gcc", "libffi-dev", "libssl-dev"] + extra_build_deps
        )
        runtime_deps_str = " \\\n                    ".join(
            ["curl", "tini"] + extra_runtime_deps
        )

        # Migration step in entrypoint
        migration_comment = ""
        if has_migrations:
            migration_comment = textwrap.dedent("""\

            # Run database migrations before starting (uncomment when ready)
            # RUN python -m aquilia.cli migrate --apply
            """)

        return textwrap.dedent(f"""\
            # syntax=docker/dockerfile:1
            # ──────────────────────────────────────────────────────────────
            # Aquilia Production Dockerfile — {name}
            # Generated by: aq deploy dockerfile
            #
            # Multi-stage build with security best-practices.
            # Override Python version at build time:
            #   docker build --build-arg PYTHON_VERSION=3.13 .
            # ──────────────────────────────────────────────────────────────

            ARG PYTHON_VERSION={python_version}

            # ── Stage 1: Builder ──────────────────────────────────────────
            FROM python:${{PYTHON_VERSION}}-slim AS builder

            WORKDIR /build

            # Install build dependencies
            RUN apt-get update && \\
                apt-get install -y --no-install-recommends \\
                    {build_deps_str} && \\
                rm -rf /var/lib/apt/lists/*

            # Install Python dependencies (cached layer — uses BuildKit cache mount)
            COPY requirements*.txt pyproject.toml setup.py* setup.cfg* ./
            RUN --mount=type=cache,target=/root/.cache/pip \\
                pip install --prefix=/install -r requirements.txt 2>/dev/null || \\
                pip install --prefix=/install . 2>/dev/null || \\
                pip install --prefix=/install -e . 2>/dev/null || true

            # Copy application source
            COPY . .

            # Compile Aquilia artifacts (manifest validation & freeze)
            RUN --mount=type=cache,target=/root/.cache/pip \\
                pip install --prefix=/install aquilia 2>/dev/null || true

            # ── Stage 2: Production ───────────────────────────────────────
            FROM python:${{PYTHON_VERSION}}-slim AS production

            # Labels for container metadata (OCI standard)
            LABEL org.opencontainers.image.title="{name}" \\
                  org.opencontainers.image.description="Aquilia application — {name}" \\
                  org.opencontainers.image.vendor="Aquilia" \\
                  org.opencontainers.image.version="${{APP_VERSION:-{self.ctx.get('version', '0.1.0')}}}" \\
                  org.opencontainers.image.created="{self.ctx.get('generated_at', '')}"

            # Security: run as non-root
            RUN groupadd -r aquilia && \\
                useradd -r -g aquilia -d /app -s /sbin/nologin aquilia

            WORKDIR /app

            # Install runtime dependencies only
            RUN apt-get update && \\
                apt-get install -y --no-install-recommends \\
                    {runtime_deps_str} && \\
                rm -rf /var/lib/apt/lists/*

            # Copy installed packages from builder
            COPY --from=builder /install /usr/local

            # Copy application code
            COPY --chown=aquilia:aquilia . .

            # Create directories for runtime data
            RUN mkdir -p /app/artifacts /app/runtime /app/.aquilia && \\
                chown -R aquilia:aquilia /app
            {migration_comment}
            # Switch to non-root user
            USER aquilia

            # Environment variables
            ENV PYTHONUNBUFFERED=1 \\
                PYTHONDONTWRITEBYTECODE=1 \\
                AQUILIA_ENV=production \\
                AQUILIA_MODE=prod \\
                AQ_SERVER_HOST=0.0.0.0 \\
                AQ_SERVER_PORT={port} \\
                AQ_SERVER_WORKERS={workers}

            # Expose port
            EXPOSE {port}

            # Health check — integrated with Aquilia fault system
            HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \\
                CMD curl -f http://localhost:{port}/health || exit 1

            # Use tini as init system for proper signal handling
            ENTRYPOINT ["tini", "--"]

            # Start Aquilia production server
            CMD ["python", "-m", "aquilia.cli", "serve", \\
                 "--workers", "{workers}", \\
                 "--bind", "0.0.0.0:{port}"]
        """)

    def generate_dockerfile_dev(self) -> str:
        """Generate development Dockerfile with hot-reload."""
        name = self.ctx["name"]
        port = self.ctx.get("port", 8000)
        python_version = self.ctx.get("python_version", "3.12")
        has_db = self.ctx.get("has_db", False)
        db_driver = self.ctx.get("db_driver", "sqlite")

        extra_deps = []
        if has_db and db_driver == "postgres":
            extra_deps.append("libpq-dev")

        extra_str = ""
        if extra_deps:
            extra_str = " \\\n                    ".join(extra_deps) + " \\\n                    "

        return textwrap.dedent(f"""\
            # syntax=docker/dockerfile:1
            # ──────────────────────────────────────────────────────────────
            # Aquilia Development Dockerfile — {name}
            # Generated by: aq deploy dockerfile --dev
            #
            # Optimised for hot-reload development with volume mounts.
            # ──────────────────────────────────────────────────────────────

            ARG PYTHON_VERSION={python_version}
            FROM python:${{PYTHON_VERSION}}-slim

            WORKDIR /app

            # Install system dependencies
            RUN apt-get update && \\
                apt-get install -y --no-install-recommends \\
                    build-essential \\
                    gcc \\
                    {extra_str}curl && \\
                rm -rf /var/lib/apt/lists/*

            # Install Python dependencies
            COPY requirements*.txt pyproject.toml setup.py* setup.cfg* ./
            RUN --mount=type=cache,target=/root/.cache/pip \\
                pip install -r requirements.txt 2>/dev/null || \\
                pip install -e ".[dev]" 2>/dev/null || \\
                pip install -e . 2>/dev/null || true

            # Install development tools
            RUN --mount=type=cache,target=/root/.cache/pip \\
                pip install watchfiles httpx pytest pytest-asyncio ruff

            # Copy application source (will be overridden by volume mount)
            COPY . .

            ENV PYTHONUNBUFFERED=1 \\
                AQUILIA_ENV=development \\
                AQUILIA_MODE=dev

            EXPOSE {port}

            # Development server with hot-reload
            CMD ["python", "-m", "aquilia.cli", "run", \\
                 "--host", "0.0.0.0", \\
                 "--port", "{port}", \\
                 "--reload"]
        """)

    def generate_dockerfile_mlops(self) -> str:
        """Generate MLOps model-serving Dockerfile with optional GPU support."""
        name = self.ctx["name"]
        python_version = self.ctx.get("python_version", "3.12")

        return textwrap.dedent(f"""\
            # syntax=docker/dockerfile:1
            # ──────────────────────────────────────────────────────────────
            # Aquilia MLOps Model Server Dockerfile — {name}
            # Generated by: aq deploy dockerfile --mlops
            #
            # Production-ready model serving with:
            # - Dynamic batching (Aquilia DynamicBatcher)
            # - Prometheus metrics export
            # - Health / readiness probes
            # - GPU passthrough support (uncomment nvidia base)
            # - BuildKit cache mounts for faster rebuilds
            # ──────────────────────────────────────────────────────────────

            ARG PYTHON_VERSION={python_version}

            # For GPU: replace with nvidia/cuda:12.2.0-runtime-ubuntu22.04
            FROM python:${{PYTHON_VERSION}}-slim AS base

            WORKDIR /app

            # Install system dependencies
            RUN apt-get update && \\
                apt-get install -y --no-install-recommends \\
                    build-essential \\
                    gcc \\
                    curl \\
                    libgomp1 && \\
                rm -rf /var/lib/apt/lists/*

            # Security: non-root user
            RUN groupadd -r mlops && \\
                useradd -r -g mlops -d /app -s /sbin/nologin mlops

            # Install Python dependencies
            COPY requirements*.txt pyproject.toml setup.py* setup.cfg* ./
            RUN --mount=type=cache,target=/root/.cache/pip \\
                pip install -r requirements.txt 2>/dev/null || \\
                pip install ".[mlops]" 2>/dev/null || true
            RUN --mount=type=cache,target=/root/.cache/pip \\
                pip install numpy torch onnxruntime 2>/dev/null || true

            # Copy application code
            COPY --chown=mlops:mlops . .

            # Create model storage directory
            RUN mkdir -p /models /app/.aquilia && \\
                chown -R mlops:mlops /models /app

            USER mlops

            ENV PYTHONUNBUFFERED=1 \\
                AQUILIA_ENV=production \\
                AQUILIA_MODEL_DIR=/models \\
                AQUILIA_BATCH_SIZE=8 \\
                AQUILIA_BATCH_LATENCY_MS=50 \\
                AQUILIA_METRICS_PORT=9090

            EXPOSE 9000 9090

            HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=3 \\
                CMD curl -f http://localhost:9000/health || exit 1

            CMD ["python", "-m", "aquilia.mlops.serving.server", \\
                 "--host", "0.0.0.0", \\
                 "--port", "9000", \\
                 "--metrics-port", "9090"]
        """)

    def generate_dockerignore(self) -> str:
        """Generate .dockerignore for efficient builds."""
        return textwrap.dedent("""\
            # ── Aquilia .dockerignore ─────────────────────────────────────
            # Generated by: aq deploy dockerfile

            # Version control
            .git
            .gitignore

            # Python
            __pycache__
            *.py[cod]
            *$py.class
            *.so
            .Python
            env/
            venv/
            .venv/
            ENV/
            .eggs/
            *.egg-info/
            *.egg
            dist/
            build/

            # Aquilia trace/runtime (regenerated)
            .aquilia/
            runtime/
            prediction_logs/

            # IDE / Editor
            .vscode/
            .idea/
            *.swp
            *.swo
            *~

            # OS
            .DS_Store
            Thumbs.db

            # Tests & docs (not needed in production image)
            tests/
            docs/
            benchmarks/
            examples/
            *.md
            !README.md

            # Docker files (avoid recursive context)
            Dockerfile*
            docker-compose*
            .dockerignore

            # CI/CD
            .github/
            .gitlab-ci.yml
            Makefile

            # Kubernetes manifests (not needed in image)
            k8s/
            deploy/
        """)


# ═══════════════════════════════════════════════════════════════════════════
# Docker Compose Generator
# ═══════════════════════════════════════════════════════════════════════════

class ComposeGenerator:
    """
    Generates production-ready docker-compose.yml for Aquilia workspaces.

    Auto-detects and provisions:
    - App service (Aquilia server) with logging driver
    - Database (PostgreSQL / MySQL / SQLite volume)
    - Redis (sessions, cache, rate-limiting)
    - Nginx reverse proxy
    - MLOps model server (if mlops detected)
    - Prometheus + Grafana (if metrics enabled)
    - MailHog (if mail detected, dev only)
    - DB migration init service (if migrations detected)
    - Compose profiles for selective service activation
    """

    def __init__(self, ctx: Dict[str, Any]):
        self.ctx = ctx

    def generate_compose(self, *, include_monitoring: bool = False) -> str:
        """Generate docker-compose.yml."""
        name = self.ctx["name"]
        port = self.ctx.get("port", 8000)
        workers = self.ctx.get("workers", 4)
        has_db = self.ctx.get("has_db", False)
        db_url = self.ctx.get("db_url", "")
        db_driver = self.ctx.get("db_driver", "sqlite")
        has_cache = self.ctx.get("has_cache", False)
        has_sessions = self.ctx.get("has_sessions", False)
        session_store = self.ctx.get("session_store", "memory")
        has_websockets = self.ctx.get("has_websockets", False)
        has_mlops = self.ctx.get("has_mlops", False)
        has_mail = self.ctx.get("has_mail", False)
        has_migrations = self.ctx.get("has_migrations", False)
        metrics_enabled = self.ctx.get("metrics_enabled", False)

        # Determine if we need Redis
        needs_redis = (
            has_cache and self.ctx.get("cache_backend") == "redis"
        ) or (
            has_sessions and session_store == "redis"
        ) or self.ctx.get("rate_limiting", False)

        # Determine database backend
        needs_postgres = has_db and db_driver == "postgres"
        needs_mysql = has_db and db_driver == "mysql"
        uses_sqlite = has_db and not needs_postgres and not needs_mysql

        sections: List[str] = []

        # ── Header ──
        svc_list = ["#   app        — Aquilia application server"]
        if needs_postgres:
            svc_list.append("#   db         — PostgreSQL database")
        if needs_mysql:
            svc_list.append("#   db         — MySQL database")
        if needs_redis:
            svc_list.append("#   redis      — Redis (sessions/cache/rate-limit)")
        svc_list.append("#   nginx      — Reverse proxy")
        if has_migrations:
            svc_list.append("#   migrate    — Database migration runner (run-once)")
        if has_mlops:
            svc_list.append("#   model      — MLOps model serving    [profile: mlops]")
        if include_monitoring or metrics_enabled:
            svc_list.append("#   prometheus — Metrics collection      [profile: monitoring]")
            svc_list.append("#   grafana    — Metrics dashboard       [profile: monitoring]")
        if has_mail:
            svc_list.append("#   mailhog    — Dev mail catcher        [profile: dev]")

        svc_block = "\n".join(svc_list)

        sections.append(textwrap.dedent(f"""\
            # ──────────────────────────────────────────────────────────────
            # Aquilia Docker Compose — {name}
            # Generated by: aq deploy compose
            #
            # Services:
        """).rstrip() + "\n" + svc_block + textwrap.dedent(f"""
            #
            # Usage:
            #   docker compose up -d
            #   docker compose --profile monitoring up -d
            #   docker compose --profile mlops up -d
            #   docker compose logs -f app
            #   docker compose down -v   (destroy volumes)
            # ──────────────────────────────────────────────────────────────
        """).rstrip())

        # ── Compose definition ──
        compose_lines = [
            "",
            "services:",
            "",
        ]

        # ── App service ──
        app_env_lines = [
            f'      AQUILIA_ENV: production',
            f'      AQUILIA_MODE: prod',
            f'      AQ_SERVER_HOST: "0.0.0.0"',
            f'      AQ_SERVER_PORT: "{port}"',
            f'      AQ_SERVER_WORKERS: "{workers}"',
        ]
        if needs_postgres:
            app_env_lines.append('      DATABASE_URL: "postgresql+asyncpg://aquilia:${DB_PASSWORD:-aquilia}@db:5432/aquilia"')
        if needs_mysql:
            app_env_lines.append('      DATABASE_URL: "mysql+aiomysql://aquilia:${DB_PASSWORD:-aquilia}@db:3306/aquilia"')
        if uses_sqlite:
            app_env_lines.append('      DATABASE_URL: "sqlite:///data/db.sqlite3"')
        if needs_redis:
            app_env_lines.append('      REDIS_URL: "redis://redis:6379/0"')
            if has_sessions and session_store == "redis":
                app_env_lines.append('      AQ_SESSION_STORE: redis')
                app_env_lines.append('      AQ_SESSION_REDIS_URL: "redis://redis:6379/1"')
            if has_cache:
                app_env_lines.append('      AQ_CACHE_BACKEND: redis')
                app_env_lines.append('      AQ_CACHE_REDIS_URL: "redis://redis:6379/2"')

        depends = []
        if needs_postgres or needs_mysql:
            depends.append("db")
        if needs_redis:
            depends.append("redis")
        if has_migrations:
            depends.append("migrate")

        depends_block = ""
        if depends:
            depends_entries = "\n".join(
                f"        {d}:\n          condition: service_{'completed_successfully' if d == 'migrate' else 'healthy'}"
                for d in depends
            )
            depends_block = f"    depends_on:\n{depends_entries}"

        app_volumes = ['      - ./:/app']
        if uses_sqlite:
            app_volumes.append('      - app-data:/app/data')
        app_volumes.append('      - app-artifacts:/app/artifacts')
        app_volumes.append('      - app-trace:/app/.aquilia')

        compose_lines.extend([
            f"  # ── Aquilia Application ──",
            f"  app:",
            f"    build:",
            f"      context: .",
            f"      dockerfile: Dockerfile",
            f"      target: production",
            f"    container_name: {name}-app",
            f"    restart: unless-stopped",
            f"    ports:",
            f'      - "{port}:{port}"',
            f"    environment:",
            *app_env_lines,
            f"    env_file:",
            f"      - .env",
            f"    volumes:",
            *app_volumes,
        ])
        if depends_block:
            compose_lines.append(depends_block)
        compose_lines.extend([
            f"    healthcheck:",
            f"      test: ['CMD', 'curl', '-f', 'http://localhost:{port}/health']",
            f"      interval: 30s",
            f"      timeout: 10s",
            f"      retries: 3",
            f"      start_period: 15s",
            f"    logging:",
            f"      driver: json-file",
            f"      options:",
            f"        max-size: '10m'",
            f"        max-file: '3'",
            f"    networks:",
            f"      - {name}-net",
            "",
        ])

        # ── Migration Service ──
        if has_migrations and (needs_postgres or needs_mysql):
            compose_lines.extend([
                f"  # ── Database Migrations (run-once) ──",
                f"  migrate:",
                f"    build:",
                f"      context: .",
                f"      dockerfile: Dockerfile",
                f"      target: production",
                f"    container_name: {name}-migrate",
                f"    command: ['python', '-m', 'aquilia.cli', 'migrate', '--apply']",
                f"    environment:",
            ])
            if needs_postgres:
                compose_lines.append('      DATABASE_URL: "postgresql+asyncpg://aquilia:${DB_PASSWORD:-aquilia}@db:5432/aquilia"')
            if needs_mysql:
                compose_lines.append('      DATABASE_URL: "mysql+aiomysql://aquilia:${DB_PASSWORD:-aquilia}@db:3306/aquilia"')
            compose_lines.extend([
                f"    depends_on:",
                f"      db:",
                f"        condition: service_healthy",
                f"    networks:",
                f"      - {name}-net",
                "",
            ])

        # ── Nginx ──
        compose_lines.extend([
            f"  # ── Nginx Reverse Proxy ──",
            f"  nginx:",
            f"    image: nginx:alpine",
            f"    container_name: {name}-nginx",
            f"    restart: unless-stopped",
            f"    ports:",
            f'      - "80:80"',
            f'      - "443:443"',
            f"    volumes:",
            f"      - ./deploy/nginx/nginx.conf:/etc/nginx/nginx.conf:ro",
            f"      - ./deploy/nginx/ssl:/etc/nginx/ssl:ro",
            f"    depends_on:",
            f"      app:",
            f"        condition: service_healthy",
            f"    healthcheck:",
            f"      test: ['CMD', 'curl', '-f', 'http://localhost/nginx-health']",
            f"      interval: 15s",
            f"      timeout: 5s",
            f"      retries: 3",
            f"    networks:",
            f"      - {name}-net",
            "",
        ])

        # ── PostgreSQL ──
        if needs_postgres:
            compose_lines.extend([
                f"  # ── PostgreSQL Database ──",
                f"  db:",
                f"    image: postgres:16-alpine",
                f"    container_name: {name}-db",
                f"    restart: unless-stopped",
                f"    environment:",
                f"      POSTGRES_DB: aquilia",
                f"      POSTGRES_USER: aquilia",
                f"      POSTGRES_PASSWORD: ${{DB_PASSWORD:-aquilia}}",
                f"    volumes:",
                f"      - postgres-data:/var/lib/postgresql/data",
                f"    ports:",
                f'      - "5432:5432"',
                f"    healthcheck:",
                f"      test: ['CMD-SHELL', 'pg_isready -U aquilia']",
                f"      interval: 10s",
                f"      timeout: 5s",
                f"      retries: 5",
                f"    logging:",
                f"      driver: json-file",
                f"      options:",
                f"        max-size: '5m'",
                f"        max-file: '2'",
                f"    networks:",
                f"      - {name}-net",
                "",
            ])

        # ── MySQL ──
        if needs_mysql:
            compose_lines.extend([
                f"  # ── MySQL Database ──",
                f"  db:",
                f"    image: mysql:8.0",
                f"    container_name: {name}-db",
                f"    restart: unless-stopped",
                f"    environment:",
                f"      MYSQL_DATABASE: aquilia",
                f"      MYSQL_USER: aquilia",
                f"      MYSQL_PASSWORD: ${{DB_PASSWORD:-aquilia}}",
                f"      MYSQL_ROOT_PASSWORD: ${{DB_ROOT_PASSWORD:-rootpass}}",
                f"    volumes:",
                f"      - mysql-data:/var/lib/mysql",
                f"    ports:",
                f'      - "3306:3306"',
                f"    healthcheck:",
                f"      test: ['CMD', 'mysqladmin', 'ping', '-h', 'localhost']",
                f"      interval: 10s",
                f"      timeout: 5s",
                f"      retries: 5",
                f"    networks:",
                f"      - {name}-net",
                "",
            ])

        # ── Redis ──
        if needs_redis:
            compose_lines.extend([
                f"  # ── Redis (Sessions / Cache / Rate-limiting) ──",
                f"  redis:",
                f"    image: redis:7-alpine",
                f"    container_name: {name}-redis",
                f"    restart: unless-stopped",
                f"    command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru --save 60 1000",
                f"    volumes:",
                f"      - redis-data:/data",
                f"    ports:",
                f'      - "6379:6379"',
                f"    healthcheck:",
                f"      test: ['CMD', 'redis-cli', 'ping']",
                f"      interval: 10s",
                f"      timeout: 5s",
                f"      retries: 5",
                f"    logging:",
                f"      driver: json-file",
                f"      options:",
                f"        max-size: '5m'",
                f"        max-file: '2'",
                f"    networks:",
                f"      - {name}-net",
                "",
            ])

        # ── MLOps Model Server (profile: mlops) ──
        if has_mlops:
            compose_lines.extend([
                f"  # ── MLOps Model Server ──",
                f"  model-server:",
                f"    build:",
                f"      context: .",
                f"      dockerfile: Dockerfile.mlops",
                f"    container_name: {name}-model-server",
                f"    restart: unless-stopped",
                f"    profiles:",
                f'      - mlops',
                f"    ports:",
                f'      - "9000:9000"',
                f'      - "9090:9090"',
                f"    environment:",
                f"      AQUILIA_ENV: production",
                f"      AQUILIA_MODEL_DIR: /models",
                f'      AQUILIA_BATCH_SIZE: "8"',
                f'      AQUILIA_BATCH_LATENCY_MS: "50"',
                f'      AQUILIA_METRICS_PORT: "9090"',
                f"    volumes:",
                f"      - model-data:/models",
                f"    healthcheck:",
                f"      test: ['CMD', 'curl', '-f', 'http://localhost:9000/health']",
                f"      interval: 15s",
                f"      timeout: 5s",
                f"      retries: 3",
                f"      start_period: 30s",
                f"    deploy:",
                f"      resources:",
                f"        limits:",
                f"          memory: 4G",
                f"        reservations:",
                f"          memory: 1G",
                f"          # devices:",
                f"          #   - driver: nvidia",
                f"          #     count: 1",
                f"          #     capabilities: [gpu]",
                f"    networks:",
                f"      - {name}-net",
                "",
            ])

        # ── Mail (profile: dev) ──
        if has_mail:
            compose_lines.extend([
                f"  # ── MailHog (Development Mail Catcher) ──",
                f"  mailhog:",
                f"    image: mailhog/mailhog:latest",
                f"    container_name: {name}-mailhog",
                f"    restart: unless-stopped",
                f"    profiles:",
                f'      - dev',
                f"    ports:",
                f'      - "1025:1025"   # SMTP',
                f'      - "8025:8025"   # Web UI',
                f"    networks:",
                f"      - {name}-net",
                "",
            ])

        # ── Monitoring (profile: monitoring) ──
        if include_monitoring or metrics_enabled:
            compose_lines.extend([
                f"  # ── Prometheus ──",
                f"  prometheus:",
                f"    image: prom/prometheus:latest",
                f"    container_name: {name}-prometheus",
                f"    restart: unless-stopped",
                f"    profiles:",
                f'      - monitoring',
                f"    ports:",
                f'      - "9091:9090"',
                f"    volumes:",
                f"      - ./deploy/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro",
                f"      - prometheus-data:/prometheus",
                f"    command:",
                f"      - '--config.file=/etc/prometheus/prometheus.yml'",
                f"      - '--storage.tsdb.retention.time=15d'",
                f"      - '--storage.tsdb.retention.size=5GB'",
                f"    networks:",
                f"      - {name}-net",
                "",
                f"  # ── Grafana ──",
                f"  grafana:",
                f"    image: grafana/grafana:latest",
                f"    container_name: {name}-grafana",
                f"    restart: unless-stopped",
                f"    profiles:",
                f'      - monitoring',
                f"    ports:",
                f'      - "3000:3000"',
                f"    environment:",
                f"      GF_SECURITY_ADMIN_USER: admin",
                f"      GF_SECURITY_ADMIN_PASSWORD: ${{GRAFANA_PASSWORD:-admin}}",
                f"      GF_INSTALL_PLUGINS: grafana-clock-panel",
                f"    volumes:",
                f"      - grafana-data:/var/lib/grafana",
                f"      - ./deploy/grafana/provisioning:/etc/grafana/provisioning:ro",
                f"    depends_on:",
                f"      - prometheus",
                f"    networks:",
                f"      - {name}-net",
                "",
            ])

        # ── Networks ──
        compose_lines.extend([
            f"# ── Networks ──",
            f"networks:",
            f"  {name}-net:",
            f"    driver: bridge",
            "",
        ])

        # ── Volumes ──
        volume_names = ["app-artifacts", "app-trace"]
        if uses_sqlite:
            volume_names.insert(0, "app-data")
        if needs_postgres:
            volume_names.append("postgres-data")
        if needs_mysql:
            volume_names.append("mysql-data")
        if needs_redis:
            volume_names.append("redis-data")
        if has_mlops:
            volume_names.append("model-data")
        if include_monitoring or metrics_enabled:
            volume_names.extend(["prometheus-data", "grafana-data"])

        compose_lines.extend([
            f"# ── Volumes ──",
            f"volumes:",
        ])
        for v in volume_names:
            compose_lines.append(f"  {v}:")
        compose_lines.append("")

        sections.append("\n".join(compose_lines))
        return "\n".join(sections)

    def generate_compose_dev(self) -> str:
        """Generate docker-compose.dev.yml for development."""
        name = self.ctx["name"]
        port = self.ctx.get("port", 8000)

        return textwrap.dedent(f"""\
            # ──────────────────────────────────────────────────────────────
            # Aquilia Docker Compose (Development) — {name}
            # Generated by: aq deploy compose --dev
            #
            # Usage:
            #   docker compose -f docker-compose.yml -f docker-compose.dev.yml up
            # ──────────────────────────────────────────────────────────────

            services:
              app:
                build:
                  context: .
                  dockerfile: Dockerfile.dev
                volumes:
                  - ./:/app
                  - /app/__pycache__
                  - /app/.aquilia
                environment:
                  AQUILIA_ENV: development
                  AQUILIA_MODE: dev
                  AQ_SERVER_HOST: "0.0.0.0"
                  AQ_SERVER_PORT: "{port}"
                command: >
                  python -m aquilia.cli run
                  --host 0.0.0.0
                  --port {port}
                  --reload
        """)


# ═══════════════════════════════════════════════════════════════════════════
# Kubernetes Generator
# ═══════════════════════════════════════════════════════════════════════════

class KubernetesGenerator:
    """
    Generates production-ready Kubernetes manifests for Aquilia workspaces.

    Generates:
    - Namespace
    - Deployment with health probes, resource limits, pod anti-affinity
    - Service (ClusterIP)
    - Ingress (with TLS)
    - ConfigMap (non-secret config)
    - Secret (credentials)
    - HPA (Horizontal Pod Autoscaler)
    - PDB (Pod Disruption Budget)
    - NetworkPolicy
    - ServiceAccount with RBAC
    - Init containers (wait-for-db, migrations)
    - CronJob for periodic maintenance
    - PersistentVolumeClaim for data
    - MLOps manifests (if detected)
    """

    def __init__(self, ctx: Dict[str, Any]):
        self.ctx = ctx

    def generate_namespace(self) -> str:
        """Generate Kubernetes namespace."""
        name = self.ctx["name"]
        return textwrap.dedent(f"""\
            apiVersion: v1
            kind: Namespace
            metadata:
              name: {name}
              labels:
                app.kubernetes.io/name: {name}
                app.kubernetes.io/managed-by: aquilia-cli
        """)

    def generate_configmap(self) -> str:
        """Generate ConfigMap for non-secret configuration."""
        name = self.ctx["name"]
        port = self.ctx.get("port", 8000)
        workers = self.ctx.get("workers", 4)

        data_lines = [
            f'  AQUILIA_ENV: "production"',
            f'  AQUILIA_MODE: "prod"',
            f'  AQ_SERVER_HOST: "0.0.0.0"',
            f'  AQ_SERVER_PORT: "{port}"',
            f'  AQ_SERVER_WORKERS: "{workers}"',
        ]
        if self.ctx.get("has_cache") and self.ctx.get("cache_backend") == "redis":
            data_lines.append(f'  AQ_CACHE_BACKEND: "redis"')
        if self.ctx.get("has_sessions") and self.ctx.get("session_store") == "redis":
            data_lines.append(f'  AQ_SESSION_STORE: "redis"')
        if self.ctx.get("metrics_enabled"):
            data_lines.append(f'  AQ_METRICS_ENABLED: "true"')
        if self.ctx.get("tracing_enabled"):
            data_lines.append(f'  AQ_TRACING_ENABLED: "true"')

        return textwrap.dedent(f"""\
            apiVersion: v1
            kind: ConfigMap
            metadata:
              name: {name}-config
              namespace: {name}
              labels:
                app.kubernetes.io/name: {name}
                app.kubernetes.io/component: config
            data:
        """) + "\n".join(data_lines) + "\n"

    def generate_secret(self) -> str:
        """Generate Secret template for credentials."""
        name = self.ctx["name"]
        secret_data: List[str] = [
            '  # Base64-encode your values: echo -n "value" | base64',
            '  AQ_SECRET_KEY: "CHANGEME_BASE64_ENCODED"',
        ]
        if self.ctx.get("has_db"):
            secret_data.append('  DATABASE_URL: "CHANGEME_BASE64_ENCODED"')
        if self.ctx.get("has_cache") or self.ctx.get("has_sessions"):
            secret_data.append('  REDIS_URL: "CHANGEME_BASE64_ENCODED"')
        if self.ctx.get("has_auth"):
            secret_data.append('  AQ_AUTH_SECRET: "CHANGEME_BASE64_ENCODED"')
            secret_data.append('  AQ_JWT_SECRET: "CHANGEME_BASE64_ENCODED"')
        if self.ctx.get("has_mail"):
            secret_data.append('  AQ_MAIL_PASSWORD: "CHANGEME_BASE64_ENCODED"')

        return textwrap.dedent(f"""\
            apiVersion: v1
            kind: Secret
            metadata:
              name: {name}-secrets
              namespace: {name}
              labels:
                app.kubernetes.io/name: {name}
                app.kubernetes.io/component: secrets
            type: Opaque
            data:
        """) + "\n".join(secret_data) + "\n"

    def generate_deployment(self) -> str:
        """Generate production Deployment manifest."""
        name = self.ctx["name"]
        port = self.ctx.get("port", 8000)
        workers = self.ctx.get("workers", 4)
        has_db = self.ctx.get("has_db", False)
        db_driver = self.ctx.get("db_driver", "sqlite")
        has_migrations = self.ctx.get("has_migrations", False)

        # Dynamic replica count based on module complexity
        module_count = self.ctx.get("module_count", 0)
        min_replicas = max(2, module_count // 3)

        annotations = [
            f'        prometheus.io/scrape: "true"',
            f'        prometheus.io/port: "{port}"',
            f'        prometheus.io/path: "/metrics"',
        ]

        # Init containers for database readiness + migrations
        init_containers = ""
        if has_db and db_driver in ("postgres", "mysql"):
            wait_cmd = {
                "postgres": "until pg_isready -h $DB_HOST -p 5432; do echo waiting for db; sleep 2; done",
                "mysql": "until mysqladmin ping -h $DB_HOST --silent; do echo waiting for db; sleep 2; done",
            }
            wait_image = {
                "postgres": "postgres:16-alpine",
                "mysql": "mysql:8.0",
            }
            init_sections = [textwrap.dedent(f"""\
                  initContainers:
                    # Wait for database to be ready
                    - name: wait-for-db
                      image: {wait_image[db_driver]}
                      command: ['sh', '-c', '{wait_cmd[db_driver]}']
                      env:
                        - name: DB_HOST
                          value: "{name}-db"
            """)]
            if has_migrations:
                init_sections.append(textwrap.dedent(f"""\
                    # Run database migrations
                    - name: run-migrations
                      image: ghcr.io/YOUR_ORG/{name}:latest
                      command: ['python', '-m', 'aquilia.cli', 'migrate', '--apply']
                      envFrom:
                        - configMapRef:
                            name: {name}-config
                        - secretRef:
                            name: {name}-secrets
                """))
            init_containers = "\n".join(init_sections)

        return textwrap.dedent(f"""\
            apiVersion: apps/v1
            kind: Deployment
            metadata:
              name: {name}-app
              namespace: {name}
              labels:
                app.kubernetes.io/name: {name}
                app.kubernetes.io/component: app
                app.kubernetes.io/managed-by: aquilia-cli
            spec:
              replicas: {min_replicas}
              revisionHistoryLimit: 5
              strategy:
                type: RollingUpdate
                rollingUpdate:
                  maxSurge: 1
                  maxUnavailable: 0
              selector:
                matchLabels:
                  app.kubernetes.io/name: {name}
                  app.kubernetes.io/component: app
              template:
                metadata:
                  labels:
                    app.kubernetes.io/name: {name}
                    app.kubernetes.io/component: app
                  annotations:
        """) + "\n".join(annotations) + textwrap.dedent(f"""
                spec:
                  serviceAccountName: {name}-sa
                  securityContext:
                    runAsNonRoot: true
                    runAsUser: 1000
                    runAsGroup: 1000
                    fsGroup: 1000
                    seccompProfile:
                      type: RuntimeDefault
        """) + (init_containers if init_containers else "") + textwrap.dedent(f"""
                  affinity:
                    podAntiAffinity:
                      preferredDuringSchedulingIgnoredDuringExecution:
                        - weight: 100
                          podAffinityTerm:
                            labelSelector:
                              matchExpressions:
                                - key: app.kubernetes.io/name
                                  operator: In
                                  values:
                                    - {name}
                            topologyKey: kubernetes.io/hostname
                  containers:
                    - name: app
                      image: ghcr.io/YOUR_ORG/{name}:latest
                      imagePullPolicy: Always
                      ports:
                        - name: http
                          containerPort: {port}
                          protocol: TCP
                      envFrom:
                        - configMapRef:
                            name: {name}-config
                        - secretRef:
                            name: {name}-secrets
                      resources:
                        requests:
                          cpu: "250m"
                          memory: "256Mi"
                        limits:
                          cpu: "1000m"
                          memory: "1Gi"
                      readinessProbe:
                        httpGet:
                          path: /health
                          port: http
                        initialDelaySeconds: 10
                        periodSeconds: 5
                        timeoutSeconds: 3
                        failureThreshold: 3
                      livenessProbe:
                        httpGet:
                          path: /health
                          port: http
                        initialDelaySeconds: 30
                        periodSeconds: 10
                        timeoutSeconds: 5
                        failureThreshold: 3
                      startupProbe:
                        httpGet:
                          path: /health
                          port: http
                        initialDelaySeconds: 5
                        periodSeconds: 5
                        failureThreshold: 10
                      volumeMounts:
                        - name: artifacts
                          mountPath: /app/artifacts
                        - name: trace
                          mountPath: /app/.aquilia
                  volumes:
                    - name: artifacts
                      emptyDir: {{}}
                    - name: trace
                      emptyDir: {{}}
                  terminationGracePeriodSeconds: 30
        """)

    def generate_service(self) -> str:
        """Generate Service manifest."""
        name = self.ctx["name"]
        port = self.ctx.get("port", 8000)

        return textwrap.dedent(f"""\
            apiVersion: v1
            kind: Service
            metadata:
              name: {name}-app
              namespace: {name}
              labels:
                app.kubernetes.io/name: {name}
                app.kubernetes.io/component: app
            spec:
              type: ClusterIP
              selector:
                app.kubernetes.io/name: {name}
                app.kubernetes.io/component: app
              ports:
                - name: http
                  port: {port}
                  targetPort: http
                  protocol: TCP
        """)

    def generate_ingress(self) -> str:
        """Generate Ingress manifest with TLS."""
        name = self.ctx["name"]
        port = self.ctx.get("port", 8000)
        has_websockets = self.ctx.get("has_websockets", False)

        annotations = [
            '    nginx.ingress.kubernetes.io/proxy-body-size: "50m"',
            '    nginx.ingress.kubernetes.io/proxy-read-timeout: "60"',
            '    nginx.ingress.kubernetes.io/proxy-send-timeout: "60"',
        ]
        if has_websockets:
            annotations.extend([
                '    nginx.ingress.kubernetes.io/proxy-http-version: "1.1"',
                '    nginx.ingress.kubernetes.io/websocket-services: "' + name + '-app"',
            ])

        annotations_str = "\n".join(annotations)

        return textwrap.dedent(f"""\
            apiVersion: networking.k8s.io/v1
            kind: Ingress
            metadata:
              name: {name}-ingress
              namespace: {name}
              labels:
                app.kubernetes.io/name: {name}
                app.kubernetes.io/component: ingress
              annotations:
                cert-manager.io/cluster-issuer: "letsencrypt-prod"
        """) + annotations_str + textwrap.dedent(f"""
            spec:
              ingressClassName: nginx
              tls:
                - hosts:
                    - {name}.example.com
                  secretName: {name}-tls
              rules:
                - host: {name}.example.com
                  http:
                    paths:
                      - path: /
                        pathType: Prefix
                        backend:
                          service:
                            name: {name}-app
                            port:
                              number: {port}
        """)

    def generate_hpa(self) -> str:
        """Generate HPA for auto-scaling."""
        name = self.ctx["name"]
        return textwrap.dedent(f"""\
            apiVersion: autoscaling/v2
            kind: HorizontalPodAutoscaler
            metadata:
              name: {name}-hpa
              namespace: {name}
              labels:
                app.kubernetes.io/name: {name}
            spec:
              scaleTargetRef:
                apiVersion: apps/v1
                kind: Deployment
                name: {name}-app
              minReplicas: 2
              maxReplicas: 10
              metrics:
                - type: Resource
                  resource:
                    name: cpu
                    target:
                      type: Utilization
                      averageUtilization: 70
                - type: Resource
                  resource:
                    name: memory
                    target:
                      type: Utilization
                      averageUtilization: 80
              behavior:
                scaleUp:
                  stabilizationWindowSeconds: 60
                  policies:
                    - type: Pods
                      value: 2
                      periodSeconds: 60
                scaleDown:
                  stabilizationWindowSeconds: 300
                  policies:
                    - type: Pods
                      value: 1
                      periodSeconds: 120
        """)

    def generate_pdb(self) -> str:
        """Generate PodDisruptionBudget."""
        name = self.ctx["name"]
        return textwrap.dedent(f"""\
            apiVersion: policy/v1
            kind: PodDisruptionBudget
            metadata:
              name: {name}-pdb
              namespace: {name}
              labels:
                app.kubernetes.io/name: {name}
            spec:
              minAvailable: 1
              selector:
                matchLabels:
                  app.kubernetes.io/name: {name}
                  app.kubernetes.io/component: app
        """)

    def generate_network_policy(self) -> str:
        """Generate NetworkPolicy for pod-level firewall."""
        name = self.ctx["name"]
        has_mlops = self.ctx.get("has_mlops", False)

        egress_rules = [
            "      # Allow DNS",
            "      - ports:",
            "          - port: 53",
            "            protocol: UDP",
            "          - port: 53",
            "            protocol: TCP",
        ]

        return textwrap.dedent(f"""\
            apiVersion: networking.k8s.io/v1
            kind: NetworkPolicy
            metadata:
              name: {name}-netpol
              namespace: {name}
              labels:
                app.kubernetes.io/name: {name}
            spec:
              podSelector:
                matchLabels:
                  app.kubernetes.io/name: {name}
              policyTypes:
                - Ingress
                - Egress
              ingress:
                - from:
                    - namespaceSelector:
                        matchLabels:
                          kubernetes.io/metadata.name: ingress-nginx
                  ports:
                    - port: {self.ctx.get("port", 8000)}
                      protocol: TCP
              egress:
        """) + "\n".join(egress_rules) + "\n"

    def generate_service_account(self) -> str:
        """Generate ServiceAccount with minimal RBAC."""
        name = self.ctx["name"]
        return textwrap.dedent(f"""\
            apiVersion: v1
            kind: ServiceAccount
            metadata:
              name: {name}-sa
              namespace: {name}
              labels:
                app.kubernetes.io/name: {name}
            automountServiceAccountToken: false
        """)

    def generate_mlops_manifests(self) -> str:
        """Generate MLOps-specific Kubernetes manifests."""
        name = self.ctx["name"]

        return textwrap.dedent(f"""\
            # ──────────────────────────────────────────────────────────────
            # MLOps Model Server — Kubernetes Manifests
            # ──────────────────────────────────────────────────────────────
            apiVersion: apps/v1
            kind: Deployment
            metadata:
              name: {name}-model-server
              namespace: {name}
              labels:
                app.kubernetes.io/name: {name}
                app.kubernetes.io/component: model-server
            spec:
              replicas: 2
              selector:
                matchLabels:
                  app.kubernetes.io/name: {name}
                  app.kubernetes.io/component: model-server
              template:
                metadata:
                  labels:
                    app.kubernetes.io/name: {name}
                    app.kubernetes.io/component: model-server
                  annotations:
                    prometheus.io/scrape: "true"
                    prometheus.io/port: "9090"
                    prometheus.io/path: "/metrics"
                spec:
                  serviceAccountName: {name}-sa
                  securityContext:
                    runAsNonRoot: true
                    runAsUser: 1000
                  containers:
                    - name: model-server
                      image: ghcr.io/YOUR_ORG/{name}-model:latest
                      ports:
                        - name: http
                          containerPort: 9000
                        - name: metrics
                          containerPort: 9090
                      env:
                        - name: AQUILIA_ENV
                          value: production
                        - name: AQUILIA_MODEL_DIR
                          value: /models
                        - name: AQUILIA_BATCH_SIZE
                          value: "8"
                        - name: AQUILIA_BATCH_LATENCY_MS
                          value: "50"
                      resources:
                        requests:
                          cpu: "500m"
                          memory: "1Gi"
                        limits:
                          cpu: "2"
                          memory: "4Gi"
                          # nvidia.com/gpu: "1"  # Uncomment for GPU
                      readinessProbe:
                        httpGet:
                          path: /health
                          port: http
                        initialDelaySeconds: 15
                        periodSeconds: 5
                      livenessProbe:
                        httpGet:
                          path: /health
                          port: http
                        initialDelaySeconds: 30
                        periodSeconds: 10
                      volumeMounts:
                        - name: models
                          mountPath: /models
                          readOnly: true
                  volumes:
                    - name: models
                      persistentVolumeClaim:
                        claimName: {name}-models-pvc
            ---
            apiVersion: v1
            kind: Service
            metadata:
              name: {name}-model-server
              namespace: {name}
              labels:
                app.kubernetes.io/name: {name}
                app.kubernetes.io/component: model-server
            spec:
              type: ClusterIP
              selector:
                app.kubernetes.io/name: {name}
                app.kubernetes.io/component: model-server
              ports:
                - name: http
                  port: 9000
                  targetPort: http
                - name: metrics
                  port: 9090
                  targetPort: metrics
            ---
            apiVersion: autoscaling/v2
            kind: HorizontalPodAutoscaler
            metadata:
              name: {name}-model-server-hpa
              namespace: {name}
            spec:
              scaleTargetRef:
                apiVersion: apps/v1
                kind: Deployment
                name: {name}-model-server
              minReplicas: 1
              maxReplicas: 8
              metrics:
                - type: Resource
                  resource:
                    name: cpu
                    target:
                      type: Utilization
                      averageUtilization: 60
            ---
            apiVersion: v1
            kind: PersistentVolumeClaim
            metadata:
              name: {name}-models-pvc
              namespace: {name}
            spec:
              accessModes:
                - ReadOnlyMany
              resources:
                requests:
                  storage: 50Gi
        """)

    def generate_cronjob(self) -> str:
        """Generate CronJob for periodic maintenance tasks."""
        name = self.ctx["name"]
        return textwrap.dedent(f"""\
            # ──────────────────────────────────────────────────────────────
            # Aquilia Maintenance CronJob
            # Runs periodic tasks: artifact cleanup, session pruning, etc.
            # ──────────────────────────────────────────────────────────────
            apiVersion: batch/v1
            kind: CronJob
            metadata:
              name: {name}-maintenance
              namespace: {name}
              labels:
                app.kubernetes.io/name: {name}
                app.kubernetes.io/component: maintenance
            spec:
              schedule: "0 3 * * *"  # Daily at 3 AM
              concurrencyPolicy: Forbid
              successfulJobsHistoryLimit: 3
              failedJobsHistoryLimit: 3
              jobTemplate:
                spec:
                  backoffLimit: 2
                  template:
                    metadata:
                      labels:
                        app.kubernetes.io/name: {name}
                        app.kubernetes.io/component: maintenance
                    spec:
                      serviceAccountName: {name}-sa
                      restartPolicy: OnFailure
                      securityContext:
                        runAsNonRoot: true
                        runAsUser: 1000
                      containers:
                        - name: maintenance
                          image: ghcr.io/YOUR_ORG/{name}:latest
                          command:
                            - python
                            - -m
                            - aquilia.cli
                            - doctor
                            - --cleanup
                          envFrom:
                            - configMapRef:
                                name: {name}-config
                            - secretRef:
                                name: {name}-secrets
                          resources:
                            requests:
                              cpu: "100m"
                              memory: "128Mi"
                            limits:
                              cpu: "500m"
                              memory: "512Mi"
        """)

    def generate_pvc(self) -> str:
        """Generate PersistentVolumeClaim for application data."""
        name = self.ctx["name"]
        return textwrap.dedent(f"""\
            apiVersion: v1
            kind: PersistentVolumeClaim
            metadata:
              name: {name}-data-pvc
              namespace: {name}
              labels:
                app.kubernetes.io/name: {name}
                app.kubernetes.io/component: storage
            spec:
              accessModes:
                - ReadWriteOnce
              resources:
                requests:
                  storage: 10Gi
              # storageClassName: standard  # Uncomment to specify storage class
        """)

    def generate_all(self) -> Dict[str, str]:
        """Generate all Kubernetes manifests as a dict of filename → content."""
        name = self.ctx["name"]
        manifests: Dict[str, str] = {
            "00-namespace.yaml": self.generate_namespace(),
            "01-service-account.yaml": self.generate_service_account(),
            "02-configmap.yaml": self.generate_configmap(),
            "03-secret.yaml": self.generate_secret(),
            "04-pvc.yaml": self.generate_pvc(),
            "05-deployment.yaml": self.generate_deployment(),
            "06-service.yaml": self.generate_service(),
            "07-ingress.yaml": self.generate_ingress(),
            "08-hpa.yaml": self.generate_hpa(),
            "09-pdb.yaml": self.generate_pdb(),
            "10-network-policy.yaml": self.generate_network_policy(),
            "11-cronjob.yaml": self.generate_cronjob(),
        }
        if self.ctx.get("has_mlops"):
            manifests["12-mlops.yaml"] = self.generate_mlops_manifests()
        return manifests


# ═══════════════════════════════════════════════════════════════════════════
# Nginx Generator
# ═══════════════════════════════════════════════════════════════════════════

class NginxGenerator:
    """Generate production-ready Nginx configuration for Aquilia."""

    def __init__(self, ctx: Dict[str, Any]):
        self.ctx = ctx

    def generate_nginx_conf(self) -> str:
        """Generate main nginx.conf."""
        name = self.ctx["name"]
        port = self.ctx.get("port", 8000)
        has_websockets = self.ctx.get("has_websockets", False)
        has_mlops = self.ctx.get("has_mlops", False)
        has_static = self.ctx.get("has_static", False)

        ws_block = ""
        if has_websockets:
            ws_block = textwrap.dedent(f"""\

                # ── WebSocket Upgrade ──
                location /ws/ {{
                    proxy_pass http://aquilia_upstream;
                    proxy_http_version 1.1;
                    proxy_set_header Upgrade $http_upgrade;
                    proxy_set_header Connection "upgrade";
                    proxy_set_header Host $host;
                    proxy_set_header X-Real-IP $remote_addr;
                    proxy_read_timeout 86400s;
                    proxy_send_timeout 86400s;
                }}
            """)

        mlops_block = ""
        if has_mlops:
            mlops_block = textwrap.dedent(f"""\

                # ── MLOps Model Server ──
                location /api/predict {{
                    proxy_pass http://model_upstream;
                    proxy_set_header Host $host;
                    proxy_set_header X-Real-IP $remote_addr;
                    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
                    proxy_set_header X-Forwarded-Proto $scheme;
                    proxy_read_timeout 120s;  # Model inference can be slow
                    proxy_buffering off;
                    client_max_body_size 100m;  # For large model inputs
                }}
            """)

        static_block = ""
        if has_static:
            static_block = textwrap.dedent("""\

                # ── Static Files ──
                location /static/ {
                    alias /app/static/;
                    expires 30d;
                    add_header Cache-Control "public, immutable";
                    access_log off;
                }
            """)

        mlops_upstream = ""
        if has_mlops:
            mlops_upstream = textwrap.dedent(f"""\

            upstream model_upstream {{
                server model-server:9000;
            }}
            """)

        return textwrap.dedent(f"""\
            # ──────────────────────────────────────────────────────────────
            # Aquilia Nginx Configuration — {name}
            # Generated by: aq deploy nginx
            # ──────────────────────────────────────────────────────────────

            worker_processes auto;
            worker_rlimit_nofile 65535;
            error_log /var/log/nginx/error.log warn;
            pid /var/run/nginx.pid;

            events {{
                worker_connections 4096;
                multi_accept on;
                use epoll;
            }}

            http {{
                # ── Basic Settings ──
                sendfile on;
                tcp_nopush on;
                tcp_nodelay on;
                keepalive_timeout 65;
                types_hash_max_size 2048;
                server_tokens off;

                # ── MIME Types ──
                include /etc/nginx/mime.types;
                default_type application/octet-stream;

                # ── Logging ──
                log_format main '$remote_addr - $remote_user [$time_local] '
                                '"$request" $status $body_bytes_sent '
                                '"$http_referer" "$http_user_agent" '
                                '$request_time $upstream_response_time';
                access_log /var/log/nginx/access.log main;

                # ── Gzip Compression ──
                gzip on;
                gzip_vary on;
                gzip_proxied any;
                gzip_comp_level 6;
                gzip_types text/plain text/css application/json application/javascript
                           text/xml application/xml application/xml+rss text/javascript;

                # ── Rate Limiting ──
                limit_req_zone $binary_remote_addr zone=api:10m rate=100r/s;
                limit_conn_zone $binary_remote_addr zone=conn:10m;

                # ── Upstreams ──
                upstream aquilia_upstream {{
                    least_conn;
                    server app:{port};
                    keepalive 32;
                }}
                {mlops_upstream}
                # ── Server Block ──
                server {{
                    listen 80;
                    server_name {name}.example.com;

                    # Redirect HTTP → HTTPS (uncomment in production)
                    # return 301 https://$host$request_uri;

                    # ── Security Headers ──
                    add_header X-Frame-Options "SAMEORIGIN" always;
                    add_header X-Content-Type-Options "nosniff" always;
                    add_header X-XSS-Protection "1; mode=block" always;
                    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
                    add_header Content-Security-Policy "default-src 'self'" always;

                    # ── Health Check ──
                    location /nginx-health {{
                        access_log off;
                        return 200 "OK";
                        add_header Content-Type text/plain;
                    }}
                    {static_block}
                    # ── API Proxy ──
                    location / {{
                        proxy_pass http://aquilia_upstream;
                        proxy_set_header Host $host;
                        proxy_set_header X-Real-IP $remote_addr;
                        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
                        proxy_set_header X-Forwarded-Proto $scheme;
                        proxy_set_header X-Request-ID $request_id;

                        # Request limits
                        limit_req zone=api burst=50 nodelay;
                        limit_conn conn 100;
                        client_max_body_size 10m;

                        # Timeouts
                        proxy_connect_timeout 10s;
                        proxy_read_timeout 60s;
                        proxy_send_timeout 60s;
                    }}
                    {ws_block}{mlops_block}
                }}

                # ── HTTPS Server (uncomment and configure) ──
                # server {{
                #     listen 443 ssl http2;
                #     server_name {name}.example.com;
                #
                #     ssl_certificate /etc/nginx/ssl/tls.crt;
                #     ssl_certificate_key /etc/nginx/ssl/tls.key;
                #     ssl_protocols TLSv1.2 TLSv1.3;
                #     ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
                #     ssl_prefer_server_ciphers on;
                #     ssl_session_cache shared:SSL:10m;
                #     ssl_session_timeout 1d;
                #     ssl_session_tickets off;
                #
                #     # HSTS
                #     add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
                #
                #     # OCSP Stapling
                #     ssl_stapling on;
                #     ssl_stapling_verify on;
                #     resolver 8.8.8.8 8.8.4.4 valid=300s;
                #     resolver_timeout 5s;
                #
                #     # Security headers (same as HTTP block)
                #     add_header X-Frame-Options "SAMEORIGIN" always;
                #     add_header X-Content-Type-Options "nosniff" always;
                #     add_header X-XSS-Protection "1; mode=block" always;
                #     add_header Referrer-Policy "strict-origin-when-cross-origin" always;
                #     add_header Content-Security-Policy "default-src 'self'" always;
                #
                #     location / {{
                #         proxy_pass http://aquilia_upstream;
                #         proxy_set_header Host $host;
                #         proxy_set_header X-Real-IP $remote_addr;
                #         proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
                #         proxy_set_header X-Forwarded-Proto $scheme;
                #         proxy_set_header X-Request-ID $request_id;
                #         limit_req zone=api burst=50 nodelay;
                #         limit_conn conn 100;
                #         client_max_body_size 10m;
                #     }}
                # }}
            }}
        """)


# ═══════════════════════════════════════════════════════════════════════════
# CI/CD Generator
# ═══════════════════════════════════════════════════════════════════════════

class CIGenerator:
    """Generate CI/CD pipelines (GitHub Actions, GitLab CI)."""

    def __init__(self, ctx: Dict[str, Any]):
        self.ctx = ctx

    def generate_github_actions(self) -> str:
        """Generate GitHub Actions CI/CD pipeline."""
        name = self.ctx["name"]
        python_version = self.ctx.get("python_version", "3.12")
        has_mlops = self.ctx.get("has_mlops", False)
        has_db = self.ctx.get("has_db", False)
        db_driver = self.ctx.get("db_driver", "sqlite")

        # Test service containers (for integration tests)
        test_services = ""
        if has_db and db_driver == "postgres":
            test_services = textwrap.dedent("""\
                services:
                  postgres:
                    image: postgres:16-alpine
                    env:
                      POSTGRES_DB: aquilia_test
                      POSTGRES_USER: aquilia
                      POSTGRES_PASSWORD: test
                    ports:
                      - 5432:5432
                    options: >-
                      --health-cmd="pg_isready -U aquilia"
                      --health-interval=10s
                      --health-timeout=5s
                      --health-retries=5
            """)

        mlops_step = ""
        if has_mlops:
            mlops_step = textwrap.dedent(f"""\

              - name: Build MLOps image
                uses: docker/build-push-action@v5
                with:
                  context: .
                  file: Dockerfile.mlops
                  push: ${{{{ github.ref == 'refs/heads/main' }}}}
                  tags: |
                    ghcr.io/${{{{ github.repository }}}}-model:latest
                    ghcr.io/${{{{ github.repository }}}}-model:${{{{ github.sha }}}}
                  cache-from: type=gha
                  cache-to: type=gha,mode=max
            """)

        return textwrap.dedent(f"""\
            # ──────────────────────────────────────────────────────────────
            # Aquilia CI/CD Pipeline — {name}
            # Generated by: aq deploy ci
            # ──────────────────────────────────────────────────────────────

            name: Aquilia CI/CD

            on:
              push:
                branches: [main, develop]
              pull_request:
                branches: [main]

            concurrency:
              group: ${{{{ github.workflow }}}}-${{{{ github.ref }}}}
              cancel-in-progress: true

            env:
              REGISTRY: ghcr.io
              IMAGE_NAME: ${{{{ github.repository }}}}

            permissions:
              contents: read

            jobs:
              # ── Lint & Validate ──
              validate:
                runs-on: ubuntu-latest
                steps:
                  - uses: actions/checkout@v4

                  - name: Set up Python
                    uses: actions/setup-python@v5
                    with:
                      python-version: "{python_version}"
                      cache: "pip"

                  - name: Install dependencies
                    run: |
                      pip install -e ".[dev]"
                      pip install ruff

                  - name: Lint
                    run: ruff check .

                  - name: Type check (optional)
                    run: ruff check --select=ANN . || true

                  - name: Validate manifests
                    run: python -m aquilia.cli validate --strict

              # ── Test ──
              test:
                runs-on: ubuntu-latest
                needs: validate
                {test_services}
                steps:
                  - uses: actions/checkout@v4

                  - name: Set up Python
                    uses: actions/setup-python@v5
                    with:
                      python-version: "{python_version}"
                      cache: "pip"

                  - name: Install dependencies
                    run: pip install -e ".[dev]"

                  - name: Run tests
                    run: python -m aquilia.cli test --coverage
                    env:
                      AQUILIA_ENV: test

                  - name: Upload coverage
                    uses: codecov/codecov-action@v4
                    with:
                      file: ./coverage.xml
                      fail_ci_if_error: false

              # ── Security Scan ──
              security:
                runs-on: ubuntu-latest
                needs: validate
                permissions:
                  security-events: write
                steps:
                  - uses: actions/checkout@v4

                  - name: Run Trivy vulnerability scanner (filesystem)
                    uses: aquasecurity/trivy-action@master
                    with:
                      scan-type: fs
                      scan-ref: .
                      format: sarif
                      output: trivy-results.sarif
                      severity: "CRITICAL,HIGH"
                    continue-on-error: true

                  - name: Upload Trivy scan results
                    uses: github/codeql-action/upload-sarif@v3
                    with:
                      sarif_file: trivy-results.sarif
                    continue-on-error: true

                  - name: Dependency audit
                    run: pip audit 2>/dev/null || true

              # ── Build & Push ──
              build:
                runs-on: ubuntu-latest
                needs: [test, security]
                if: github.event_name == 'push'
                permissions:
                  contents: read
                  packages: write
                steps:
                  - uses: actions/checkout@v4

                  - name: Login to GHCR
                    uses: docker/login-action@v3
                    with:
                      registry: ${{{{ env.REGISTRY }}}}
                      username: ${{{{ github.actor }}}}
                      password: ${{{{ secrets.GITHUB_TOKEN }}}}

                  - name: Set up Docker Buildx
                    uses: docker/setup-buildx-action@v3

                  - name: Extract metadata
                    id: meta
                    uses: docker/metadata-action@v5
                    with:
                      images: ${{{{ env.REGISTRY }}}}/${{{{ env.IMAGE_NAME }}}}
                      tags: |
                        type=ref,event=branch
                        type=sha
                        type=semver,pattern={{{{version}}}}

                  - name: Build and push app image
                    uses: docker/build-push-action@v5
                    with:
                      context: .
                      file: Dockerfile
                      push: ${{{{ github.ref == 'refs/heads/main' }}}}
                      tags: ${{{{ steps.meta.outputs.tags }}}}
                      labels: ${{{{ steps.meta.outputs.labels }}}}
                      cache-from: type=gha
                      cache-to: type=gha,mode=max

                  - name: Scan built image with Trivy
                    uses: aquasecurity/trivy-action@master
                    with:
                      image-ref: ${{{{ env.REGISTRY }}}}/${{{{ env.IMAGE_NAME }}}}:${{{{ github.sha }}}}
                      format: table
                      severity: "CRITICAL,HIGH"
                    continue-on-error: true
                      {mlops_step}
              # ── Deploy ──
              deploy:
                runs-on: ubuntu-latest
                needs: build
                if: github.ref == 'refs/heads/main'
                environment: production
                permissions:
                  contents: read
                  id-token: write
                steps:
                  - uses: actions/checkout@v4

                  - name: Deploy to Kubernetes
                    run: |
                      echo "Deploy step — configure with your k8s cluster"
                      # kubectl apply -k k8s/
                      # or: helm upgrade --install {name} ./helm/
        """)

    def generate_gitlab_ci(self) -> str:
        """Generate GitLab CI/CD pipeline."""
        name = self.ctx["name"]
        python_version = self.ctx.get("python_version", "3.12")
        has_mlops = self.ctx.get("has_mlops", False)

        mlops_build = ""
        if has_mlops:
            mlops_build = textwrap.dedent(f"""\

            build-mlops:
              stage: build
              image: docker:24
              services:
                - docker:24-dind
              script:
                - docker build -f Dockerfile.mlops -t $CI_REGISTRY_IMAGE/model:$CI_COMMIT_SHA .
                - docker push $CI_REGISTRY_IMAGE/model:$CI_COMMIT_SHA
              rules:
                - if: $CI_COMMIT_BRANCH == "main"
            """)

        return textwrap.dedent(f"""\
            # ──────────────────────────────────────────────────────────────
            # Aquilia GitLab CI/CD Pipeline — {name}
            # Generated by: aq deploy ci --provider=gitlab
            # ──────────────────────────────────────────────────────────────

            stages:
              - validate
              - test
              - security
              - build
              - deploy

            default:
              image: python:{python_version}-slim

            variables:
              PIP_CACHE_DIR: "$CI_PROJECT_DIR/.cache/pip"

            cache:
              paths:
                - .cache/pip

            # ── Validate ──
            lint:
              stage: validate
              script:
                - pip install ruff
                - ruff check .

            validate-manifests:
              stage: validate
              script:
                - pip install -e ".[dev]"
                - python -m aquilia.cli validate --strict

            # ── Test ──
            test:
              stage: test
              script:
                - pip install -e ".[dev]"
                - python -m aquilia.cli test --coverage
              coverage: '/TOTAL.*\\s+(\\d+%)/'
              artifacts:
                reports:
                  coverage_report:
                    coverage_format: cobertura
                    path: coverage.xml
                when: always

            # ── Security ──
            dependency-scan:
              stage: security
              script:
                - pip install pip-audit
                - pip audit || true
              allow_failure: true

            container-scan:
              stage: security
              image: docker:24
              services:
                - docker:24-dind
              script:
                - docker build -t $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA .
                - |
                  apk add --no-cache curl
                  curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh
                  trivy image --severity HIGH,CRITICAL $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA
              allow_failure: true
              rules:
                - if: $CI_COMMIT_BRANCH == "main"

            # ── Build ──
            build-app:
              stage: build
              image: docker:24
              services:
                - docker:24-dind
              script:
                - docker login -u $CI_REGISTRY_USER -p $CI_REGISTRY_PASSWORD $CI_REGISTRY
                - docker build -t $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA -t $CI_REGISTRY_IMAGE:latest .
                - docker push $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA
                - docker push $CI_REGISTRY_IMAGE:latest
              rules:
                - if: $CI_COMMIT_BRANCH == "main"
            {mlops_build}
            # ── Deploy ──
            deploy-production:
              stage: deploy
              environment:
                name: production
              script:
                - echo "Deploy step — configure with your k8s cluster"
                # - kubectl apply -k k8s/
              rules:
                - if: $CI_COMMIT_BRANCH == "main"
                  when: manual
        """)


# ═══════════════════════════════════════════════════════════════════════════
# Prometheus Config Generator
# ═══════════════════════════════════════════════════════════════════════════

class PrometheusGenerator:
    """Generate Prometheus configuration."""

    def __init__(self, ctx: Dict[str, Any]):
        self.ctx = ctx

    def generate_prometheus_yml(self) -> str:
        """Generate prometheus.yml config."""
        name = self.ctx["name"]
        port = self.ctx.get("port", 8000)
        has_mlops = self.ctx.get("has_mlops", False)

        scrape_configs = [
            textwrap.dedent(f"""\
                - job_name: "{name}-app"
                  scrape_interval: 15s
                  static_configs:
                    - targets: ["app:{port}"]
                  metrics_path: /metrics
            """),
        ]

        if has_mlops:
            scrape_configs.append(
                textwrap.dedent(f"""\
                    - job_name: "{name}-model-server"
                      scrape_interval: 15s
                      static_configs:
                        - targets: ["model-server:9090"]
                      metrics_path: /metrics
                """)
            )

        configs_str = "\n".join(f"    {line}" for sc in scrape_configs for line in sc.splitlines())

        return textwrap.dedent(f"""\
            # ──────────────────────────────────────────────────────────────
            # Prometheus Configuration — {name}
            # Generated by: aq deploy monitoring
            # ──────────────────────────────────────────────────────────────

            global:
              scrape_interval: 15s
              evaluation_interval: 15s

            scrape_configs:
        """) + configs_str + "\n"


# ═══════════════════════════════════════════════════════════════════════════
# Grafana Provisioning Generator
# ═══════════════════════════════════════════════════════════════════════════

class GrafanaGenerator:
    """Generate Grafana provisioning configuration."""

    def __init__(self, ctx: Dict[str, Any]):
        self.ctx = ctx

    def generate_datasource(self) -> str:
        """Generate Grafana datasource provisioning."""
        return textwrap.dedent("""\
            # Grafana Datasource Provisioning
            # Generated by: aq deploy monitoring

            apiVersion: 1
            datasources:
              - name: Prometheus
                type: prometheus
                access: proxy
                url: http://prometheus:9090
                isDefault: true
                editable: false
        """)

    def generate_dashboard_provisioning(self) -> str:
        """Generate Grafana dashboard provisioning config."""
        return textwrap.dedent("""\
            # Grafana Dashboard Provisioning
            # Generated by: aq deploy monitoring

            apiVersion: 1
            providers:
              - name: Aquilia
                orgId: 1
                folder: Aquilia
                type: file
                disableDeletion: false
                editable: true
                options:
                  path: /etc/grafana/provisioning/dashboards
                  foldersFromFilesStructure: false
        """)


# ═══════════════════════════════════════════════════════════════════════════
# Env File Generator
# ═══════════════════════════════════════════════════════════════════════════

class EnvGenerator:
    """Generate .env templates for local and production."""

    def __init__(self, ctx: Dict[str, Any]):
        self.ctx = ctx

    def generate_env_example(self) -> str:
        """Generate .env.example template."""
        name = self.ctx["name"]
        lines = [
            f"# ── Aquilia Environment — {name} ──",
            f"# Generated by: aq deploy env",
            f"# Copy to .env and fill in real values",
            f"# NEVER commit .env to version control!",
            "",
            "# ── Application ──",
            "AQUILIA_ENV=production",
            "AQUILIA_MODE=prod",
            f"AQ_SECRET_KEY=change-me-to-a-long-random-string",
            "",
            f"# ── Server ──",
            f'AQ_SERVER_HOST=0.0.0.0',
            f'AQ_SERVER_PORT={self.ctx.get("port", 8000)}',
            f'AQ_SERVER_WORKERS={self.ctx.get("workers", 4)}',
        ]

        if self.ctx.get("has_db"):
            db_driver = self.ctx.get("db_driver", "sqlite")
            lines.extend([
                "",
                "# ── Database ──",
            ])
            if db_driver == "postgres":
                lines.append('DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/dbname')
                lines.append('DB_PASSWORD=change-me')
            elif db_driver == "mysql":
                lines.append('DATABASE_URL=mysql+aiomysql://user:pass@localhost:3306/dbname')
                lines.append('DB_PASSWORD=change-me')
                lines.append('DB_ROOT_PASSWORD=change-me-root')
            else:
                lines.append('DATABASE_URL=sqlite:///db.sqlite3')

        if self.ctx.get("has_cache") or self.ctx.get("has_sessions"):
            lines.extend([
                "",
                "# ── Redis ──",
                "REDIS_URL=redis://localhost:6379/0",
            ])

        if self.ctx.get("has_sessions"):
            lines.extend([
                "",
                "# ── Sessions ──",
                f'AQ_SESSION_STORE={self.ctx.get("session_store", "memory")}',
                "AQ_SESSION_REDIS_URL=redis://localhost:6379/1",
            ])

        if self.ctx.get("has_auth"):
            lines.extend([
                "",
                "# ── Auth ──",
                "AQ_AUTH_SECRET=change-me",
                "AQ_JWT_SECRET=change-me-jwt-secret",
                "AQ_JWT_EXPIRY=3600",
            ])

        if self.ctx.get("has_mail"):
            lines.extend([
                "",
                "# ── Mail ──",
                "AQ_MAIL_HOST=smtp.example.com",
                "AQ_MAIL_PORT=587",
                "AQ_MAIL_USER=noreply@example.com",
                "AQ_MAIL_PASSWORD=change-me",
                'AQ_MAIL_FROM="Aquilia App <noreply@example.com>"',
            ])

        if self.ctx.get("has_mlops"):
            lines.extend([
                "",
                "# ── MLOps ──",
                "AQUILIA_MODEL_DIR=/models",
                "AQUILIA_BATCH_SIZE=8",
                "AQUILIA_BATCH_LATENCY_MS=50",
            ])

        if self.ctx.get("metrics_enabled") or self.ctx.get("tracing_enabled"):
            lines.extend([
                "",
                "# ── Telemetry ──",
            ])
            if self.ctx.get("metrics_enabled"):
                lines.append("AQ_METRICS_ENABLED=true")
            if self.ctx.get("tracing_enabled"):
                lines.append("AQ_TRACING_ENABLED=true")

        if self.ctx.get("cors_enabled"):
            lines.extend([
                "",
                "# ── CORS ──",
                'AQ_CORS_ORIGINS=https://example.com,https://app.example.com',
            ])

        # Docker/monitoring
        lines.extend([
            "",
            "# ── Monitoring ──",
            "GRAFANA_PASSWORD=admin",
        ])

        lines.append("")
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════
# Makefile Generator
# ═══════════════════════════════════════════════════════════════════════════

class MakefileGenerator:
    """
    Generate a production-ready Makefile for Aquilia workspaces.

    Provides convenient shortcuts for common development and deployment
    operations: build, run, test, lint, deploy, docker, k8s, etc.
    """

    def __init__(self, ctx: Dict[str, Any]):
        self.ctx = ctx

    def generate_makefile(self) -> str:
        """Generate Makefile with comprehensive targets."""
        name = self.ctx["name"]
        port = self.ctx.get("port", 8000)
        python_version = self.ctx.get("python_version", "3.12")
        has_db = self.ctx.get("has_db", False)
        has_mlops = self.ctx.get("has_mlops", False)
        has_migrations = self.ctx.get("has_migrations", False)

        migration_targets = ""
        if has_migrations or has_db:
            migration_targets = textwrap.dedent(f"""\

            ## ── Database ────────────────────────────────────────────────────
            .PHONY: migrate migrate-create db-reset

            migrate:  ## Apply database migrations
            \t@echo "Running migrations..."
            \tpython -m aquilia.cli migrate --apply

            migrate-create:  ## Create a new migration
            \t@echo "Creating migration..."
            \tpython -m aquilia.cli migrate create $(name)

            db-reset:  ## Reset database (WARNING: destructive)
            \t@echo "Resetting database..."
            \tpython -m aquilia.cli migrate reset --confirm
            """)

        mlops_targets = ""
        if has_mlops:
            mlops_targets = textwrap.dedent(f"""\

            ## ── MLOps ───────────────────────────────────────────────────────
            .PHONY: docker-mlops docker-compose-mlops

            docker-mlops:  ## Build MLOps model server image
            \t@echo "Building MLOps image..."
            \tdocker build -f Dockerfile.mlops -t {name}-model:latest .

            docker-compose-mlops:  ## Start stack with MLOps model server
            \t@echo "Starting with MLOps..."
            \tdocker compose --profile mlops up -d
            """)

        return textwrap.dedent(f"""\
            # ──────────────────────────────────────────────────────────────
            # Aquilia Makefile — {name}
            # Generated by: aq deploy makefile
            #
            # Usage: make <target>
            #   make help        — Show all targets
            #   make dev         — Start dev server
            #   make docker-up   — Start Docker stack
            # ──────────────────────────────────────────────────────────────

            .DEFAULT_GOAL := help
            SHELL := /bin/bash

            # Variables (override with: make PORT=3000 dev)
            PORT ?= {port}
            WORKERS ?= {self.ctx.get('workers', 4)}
            PYTHON_VERSION ?= {python_version}
            IMAGE_NAME ?= {name}
            COMPOSE_PROFILES ?=

            ## ── Development ─────────────────────────────────────────────────
            .PHONY: dev run install test lint validate clean help

            dev:  ## Start development server with hot-reload
            \t@echo "🚀 Starting Aquilia dev server on port $(PORT)..."
            \tpython -m aquilia.cli run --host 0.0.0.0 --port $(PORT) --reload

            run:  ## Start production server locally
            \t@echo "🚀 Starting Aquilia production server..."
            \tpython -m aquilia.cli serve --workers $(WORKERS) --bind 0.0.0.0:$(PORT)

            install:  ## Install dependencies
            \t@echo "📦 Installing dependencies..."
            \tpip install -e ".[dev]"

            test:  ## Run test suite
            \t@echo "🧪 Running tests..."
            \tpython -m aquilia.cli test --coverage

            lint:  ## Run linter
            \t@echo "🔍 Linting..."
            \truff check .

            lint-fix:  ## Auto-fix lint issues
            \truff check --fix .

            validate:  ## Validate Aquilia manifests
            \t@echo "✓  Validating manifests..."
            \tpython -m aquilia.cli validate --strict

            compile:  ## Compile manifests to artifacts
            \t@echo "📦 Compiling artifacts..."
            \tpython -m aquilia.cli compile

            doctor:  ## Diagnose workspace issues
            \t@echo "🩺 Running diagnostics..."
            \tpython -m aquilia.cli doctor

            clean:  ## Clean build artifacts and caches
            \t@echo "🧹 Cleaning..."
            \tfind . -type d -name __pycache__ -exec rm -rf {{}} + 2>/dev/null || true
            \tfind . -type d -name "*.egg-info" -exec rm -rf {{}} + 2>/dev/null || true
            \trm -rf .aquilia/cache build/ dist/ .pytest_cache/ .coverage coverage.xml htmlcov/

            ## ── Docker ──────────────────────────────────────────────────────
            .PHONY: docker-build docker-build-dev docker-up docker-down docker-logs docker-shell docker-prune

            docker-build:  ## Build production Docker image
            \t@echo "Building production image..."
            \tDOCKER_BUILDKIT=1 docker build \\
            \t\t--build-arg PYTHON_VERSION=$(PYTHON_VERSION) \\
            \t\t-t $(IMAGE_NAME):latest \\
            \t\t-t $(IMAGE_NAME):$$(git rev-parse --short HEAD 2>/dev/null || echo "dev") \\
            \t\t.

            docker-build-dev:  ## Build development Docker image
            \t@echo "Building development image..."
            \tDOCKER_BUILDKIT=1 docker build -f Dockerfile.dev -t $(IMAGE_NAME):dev .

            docker-up:  ## Start Docker Compose stack
            \t@echo "Starting Docker stack..."
            \tdocker compose up -d

            docker-up-monitoring:  ## Start with monitoring (Prometheus + Grafana)
            \t@echo "Starting with monitoring..."
            \tdocker compose --profile monitoring up -d

            docker-down:  ## Stop Docker Compose stack
            \t@echo "Stopping Docker stack..."
            \tdocker compose down

            docker-down-clean:  ## Stop and remove volumes
            \t@echo "Stopping and cleaning volumes..."
            \tdocker compose down -v

            docker-logs:  ## Follow Docker Compose logs
            \tdocker compose logs -f app

            docker-shell:  ## Open a shell in the app container
            \tdocker compose exec app /bin/sh

            docker-prune:  ## Remove unused Docker resources
            \tdocker system prune -f --volumes

            ## ── Kubernetes ──────────────────────────────────────────────────
            .PHONY: k8s-apply k8s-delete k8s-status k8s-logs k8s-port-forward

            k8s-apply:  ## Apply Kubernetes manifests
            \t@echo "Applying Kubernetes manifests..."
            \tkubectl apply -k k8s/

            k8s-delete:  ## Delete Kubernetes resources
            \t@echo "Deleting Kubernetes resources..."
            \tkubectl delete -k k8s/

            k8s-status:  ## Show Kubernetes resource status
            \tkubectl get all -n {name}

            k8s-logs:  ## Follow app pod logs
            \tkubectl logs -n {name} -l app.kubernetes.io/name={name} -f

            k8s-port-forward:  ## Port-forward to local machine
            \tkubectl port-forward -n {name} svc/{name}-app $(PORT):$(PORT)
            {migration_targets}{mlops_targets}
            ## ── Deployment ──────────────────────────────────────────────────
            .PHONY: deploy-gen deploy-gen-all

            deploy-gen:  ## Regenerate all deployment files
            \t@echo "Regenerating deployment files..."
            \tpython -m aquilia.cli deploy all

            deploy-gen-all:  ## Regenerate all deployment files with monitoring
            \tpython -m aquilia.cli deploy all --monitoring

            ## ── Help ────────────────────────────────────────────────────────

            help:  ## Show this help message
            \t@echo ""
            \t@echo "  Aquilia — {name}"
            \t@echo ""
            \t@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \\
            \t\tawk 'BEGIN {{FS = ":.*?## "}}; {{printf "  \\033[36m%-20s\\033[0m %s\\n", $$1, $$2}}'
            \t@echo ""
        """)
