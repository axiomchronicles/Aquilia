# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Aquilia Starter section in QuickStart
- MLOps regression tests

### Fixed
- Annotation fixes and cleanups
- Docker and compose generator behavior in CLI
- Serializer parsing for `multipart/formdata`
- Authentication token augmentation issues
- CLI/MLOps command failures during press
- Navigation bar overlapping and responsiveness issues on small devices
- MLOps dependency configuration

### Changed
- Documentation hosting setup on Netlify
- Significant incremental documentation updates (Update 21 through 26)

## [1.0.0] - Initial Release

### Added
- Manifest-First Architecture implementation (`AppManifest`)
- Scoped Dependency Injection framework targeting Singleton, App, and Request contexts.
- Async-Native core using Uvicorn and ASGI specifications.
- Foundation for Integrated MLOps (Artifact Registry, Lineage Tracing, Shadow Deployments).
- Core subsystems: Flow (routing), Faults (error handling), and essential services.
