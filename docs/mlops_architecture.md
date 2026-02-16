# Aquilia MLOps Platform — Architecture Document

> **Version**: 1.0.0  
> **Date**: 2026-02-16  
> **Status**: Implementation Spec  

---

## 1. Overview

The Aquilia MLOps Platform extends the existing Aquilia web framework with a production-ready, extensible "model packaging → registry → serve → observe → release" pipeline. It preserves full backward compatibility with Aquilia's existing public APIs while adding first-class ML model lifecycle management.

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLI Layer (aq pack / serve / deploy)     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────────┐  │
│  │Modelpack │  │ Registry │  │ Runtime  │  │  Observability│  │
│  │ Builder  │  │ Service  │  │ Manager  │  │  & Drift      │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └───────┬───────┘  │
│       │              │             │                │           │
│  ┌────▼─────┐  ┌────▼─────┐  ┌────▼─────┐  ┌──────▼────────┐  │
│  │ Content  │  │ Storage  │  │ Serving  │  │  Metrics &    │  │
│  │ Store    │  │ Adapters │  │ Layer    │  │  Logging      │  │
│  └──────────┘  └──────────┘  └──────────┘  └───────────────┘  │
│                                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────────┐  │
│  │Optimizer │  │ Scheduler│  │ Release  │  │    Plugin     │  │
│  │ Pipeline │  │& Batching│  │ Manager  │  │    System     │  │
│  └──────────┘  └──────────┘  └──────────┘  └───────────────┘  │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                    Aquilia Core Framework                       │
│  (DI · Middleware · Controllers · ASGI · Lifecycle · Faults)   │
└─────────────────────────────────────────────────────────────────┘
```

## 3. Module Layout

```
aquilia/
  mlops/
    __init__.py                  # Public API surface
    _types.py                    # Shared type definitions
    pack/
      __init__.py
      builder.py                 # Modelpack creation
      manifest_schema.py         # JSON Schema for manifest.json
      signer.py                  # GPG/RSA artifact signing
      content_store.py           # Content-addressable blob store
    registry/
      __init__.py
      service.py                 # Registry HTTP API service
      models.py                  # SQLite/Postgres data models
      storage/
        __init__.py
        base.py                  # Storage adapter interface
        filesystem.py            # Local FS adapter
        s3.py                    # S3/MinIO adapter
    runtime/
      __init__.py
      base.py                    # Runtime interface
      python_runtime.py          # In-process Python runtime
      onnx_runtime.py            # ONNX Runtime adapter
      triton_adapter.py          # Triton Inference Server
      torchserve_exporter.py     # TorchServe exporter
      bento_exporter.py          # BentoML exporter
    serving/
      __init__.py
      server.py                  # Dev/prod serving layer
      batching.py                # Dynamic batching scheduler
      router.py                  # Traffic routing (canary/AB)
    optimizer/
      __init__.py
      pipeline.py                # Optimization pipeline
      quantize.py                # Quantization helpers
      export.py                  # Edge exports (TFLite/CoreML)
    observe/
      __init__.py
      metrics.py                 # Prometheus metrics
      drift.py                   # PSI/KS drift detection
      logger.py                  # Feature/prediction logging
    scheduler/
      __init__.py
      autoscaler.py              # K8s HPA metrics + autoscaling
      placement.py               # Hardware-aware placement
    release/
      __init__.py
      rollout.py                 # Canary/AB/shadow rollouts
      ci.py                      # CI/CD templates & action
    security/
      __init__.py
      signing.py                 # Artifact signing & verification
      encryption.py              # Encryption at rest
      rbac.py                    # Registry RBAC
    explain/
      __init__.py
      hooks.py                   # SHAP/LIME explainability
      privacy.py                 # PII redaction
    plugins/
      __init__.py
      host.py                    # Plugin loader & lifecycle
      marketplace.py             # Plugin marketplace API
      example_plugin.py          # Example plugin
```

## 4. Sequence Flows

### 4.1 Pack → Publish → Serve

```
Developer          CLI              Builder         ContentStore      Registry
    │                │                │                 │                │
    │─aq pack save──▶│                │                 │                │
    │                │─build_pack()──▶│                 │                │
    │                │                │─store_blobs()──▶│                │
    │                │                │◀─digests────────│                │
    │                │                │─sign_manifest()─│                │
    │                │◀─pack_path─────│                 │                │
    │                │                │                 │                │
    │─aq pack push──▶│                │                 │                │
    │                │─publish()──────│─────────────────│───────────────▶│
    │                │                │                 │                │
    │─aq serve──────▶│                │                 │                │
    │                │─fetch()────────│─────────────────│───────────────▶│
    │                │◀─modelpack─────│─────────────────│────────────────│
    │                │─Runtime.load()─│                 │                │
    │                │─start_server()─│                 │                │
    │◀─serving───────│                │                 │                │
```

### 4.2 Inference with Batching

```
Client        ServingLayer       Batcher          Runtime        Metrics
  │               │                │                │               │
  │─POST /infer──▶│                │                │               │
  │               │─enqueue()─────▶│                │               │
  │               │                │─[wait batch]───│               │
  │               │                │─infer(batch)──▶│               │
  │               │                │◀─results───────│               │
  │               │                │─emit_metrics()─│──────────────▶│
  │◀─response─────│◀─result────────│                │               │
```

## 5. Data Models

### 5.1 Modelpack Manifest Schema
See `aquilia/mlops/pack/manifest_schema.py` for full JSON Schema.

### 5.2 Registry Database
- `packs` table: name, tag, digest, manifest_json, created_at, signed_by
- `blobs` table: digest, size, storage_path, created_at
- `tags` table: name, tag, digest (mutable pointer)

## 6. API Contracts

### 6.1 Registry REST API
- `POST   /v1/packs`                  — Upload & sign modelpack
- `GET    /v1/packs/{name}:{tag}`     — Fetch pack by name:tag
- `GET    /v1/packs/{digest}`         — Fetch pack by digest
- `GET    /v1/packs/{name}/versions`  — List versions
- `POST   /v1/packs/{name}:{tag}/promote` — Promote to environment
- `DELETE /v1/packs/{name}:{tag}`     — Delete (admin only)

### 6.2 Serving API
- `POST   /v1/serve/{model}/predict`  — Run inference
- `GET    /v1/serve/{model}/health`   — Health check
- `GET    /v1/serve/{model}/metrics`  — Prometheus metrics
- `POST   /v1/serve/{model}/explain`  — Explainability endpoint

### 6.3 Rollout API
- `POST   /v1/rollouts`               — Create rollout
- `GET    /v1/rollouts/{id}`           — Get rollout status
- `POST   /v1/rollouts/{id}/advance`   — Advance canary %
- `POST   /v1/rollouts/{id}/rollback`  — Rollback

## 7. CLI Commands

| Command | Description |
|---------|-------------|
| `aq pack save` | Create modelpack from model files |
| `aq pack push` | Push modelpack to registry |
| `aq pack pull` | Pull modelpack from registry |
| `aq pack inspect` | Show modelpack manifest |
| `aq dev` | Dev server with hot-reload |
| `aq serve --model` | Serve model with runtime selection |
| `aq deploy` | Deploy to K8s or cloud |
| `aq monitor enable` | Enable observability |
| `aq rollout` | Stage traffic rollout |
| `aq export` | Export to edge format |
| `aq plugin install` | Install plugin from marketplace |

## 8. Acceptance Criteria

1. **Unit Tests**: ≥90% coverage for all `aquilia/mlops/` modules
2. **Integration**: Pack → unpack → serve → infer cycle passes
3. **Registry**: Publish → fetch → verify signature cycle passes
4. **Performance**: p95 latency < 50ms for batch_size=1 baseline model
5. **Security**: Signed artifacts verified; encrypted storage functional
6. **Observability**: Prometheus metrics emitted correctly
7. **CI**: GitHub Action template validates and runs

## 9. Rollout Plan

| Milestone | Deliverables | DoD |
|-----------|-------------|-----|
| M1: Core Pack | Builder, manifest schema, content store, signer | Pack/unpack round-trip passes |
| M2: Registry | HTTP service, SQLite backend, FS storage | Publish/fetch/verify cycle |
| M3: Runtime | Python runtime, ONNX adapter, batching | Inference e2e passes |
| M4: Serving | Dev server, production router, traffic routing | Canary rollout works |
| M5: Observe | Metrics, drift detection, logging | Dashboard shows metrics |
| M6: Optimize | Quantize, edge export, compilation | Size/latency benchmarks pass |
| M7: Release | CI templates, rollout CLI, autoscaling | Full pipeline e2e |
| M8: Plugins | Plugin host, marketplace API, example | Plugin load/unload works |
