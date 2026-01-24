"""
Fingerprint generator for reproducible deployments.

Generates deterministic SHA-256 fingerprints from registry state.
"""

import hashlib
import json
from typing import Any, Dict, List
from datetime import datetime, timezone


class FingerprintGenerator:
    """
    Generates deterministic fingerprints for registry state.
    
    Fingerprint includes:
    - App manifests (names, versions, dependencies)
    - Config schemas (structure only, not values)
    - Route metadata (paths, methods, handlers)
    - Dependency graph
    
    Excludes:
    - Runtime state
    - Timestamps (except generation time)
    - Environment-specific paths
    """
    
    def generate(
        self,
        app_contexts: List[Any],
        config: Any,
        mode: Any,
    ) -> str:
        """
        Generate fingerprint from registry state.
        
        Args:
            app_contexts: List of AppContext objects
            config: Config object
            mode: RegistryMode
            
        Returns:
            SHA-256 hex digest string
        """
        # Build canonical representation
        canonical = self._build_canonical_repr(app_contexts, config, mode)
        
        # Serialize to JSON with sorted keys
        json_str = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
        
        # Generate SHA-256 hash
        hash_obj = hashlib.sha256(json_str.encode("utf-8"))
        return hash_obj.hexdigest()
    
    def _build_canonical_repr(
        self,
        app_contexts: List[Any],
        config: Any,
        mode: Any,
    ) -> Dict[str, Any]:
        """
        Build canonical representation of registry state.
        
        Must be deterministic across:
        - Python versions
        - Operating systems
        - File system paths
        - Time zones
        
        Args:
            app_contexts: List of AppContext objects
            config: Config object
            mode: RegistryMode
            
        Returns:
            Canonical dict representation
        """
        return {
            "version": "1.0",
            "mode": mode.value,
            "apps": [
                self._canonicalize_app(ctx) for ctx in sorted(
                    app_contexts,
                    key=lambda c: c.name,
                )
            ],
            "config_schema": self._extract_config_schema(config),
            "dependency_graph": self._build_dependency_graph(app_contexts),
        }
    
    def _canonicalize_app(self, ctx: Any) -> Dict[str, Any]:
        """
        Canonicalize app context.
        
        Args:
            ctx: AppContext object
            
        Returns:
            Canonical dict
        """
        return {
            "name": ctx.name,
            "version": ctx.version,
            "depends_on": sorted(ctx.depends_on),
            "controllers": sorted(ctx.controllers),
            "services": sorted(ctx.services),
            "middlewares": sorted(
                [
                    {"path": path, "kwargs": self._canonicalize_dict(kwargs)}
                    for path, kwargs in ctx.middlewares
                ],
                key=lambda m: m["path"],
            ),
            "has_startup_hook": ctx.on_startup is not None,
            "has_shutdown_hook": ctx.on_shutdown is not None,
        }
    
    def _extract_config_schema(self, config: Any) -> Dict[str, Any]:
        """
        Extract config schema (structure only, no values).
        
        Args:
            config: Config object
            
        Returns:
            Schema dict
        """
        if config is None:
            return {}
        
        schema: Dict[str, Any] = {}
        
        # Extract field types (not values)
        for key in dir(config):
            if key.startswith("_"):
                continue
            
            value = getattr(config, key)
            
            if callable(value):
                continue
            
            schema[key] = self._get_type_signature(value)
        
        return schema
    
    def _get_type_signature(self, value: Any) -> str:
        """
        Get type signature for value.
        
        Args:
            value: Value to inspect
            
        Returns:
            Type signature string
        """
        if value is None:
            return "null"
        elif isinstance(value, bool):
            return "bool"
        elif isinstance(value, int):
            return "int"
        elif isinstance(value, float):
            return "float"
        elif isinstance(value, str):
            return "str"
        elif isinstance(value, list):
            return "list"
        elif isinstance(value, dict):
            return "dict"
        elif isinstance(value, tuple):
            return "tuple"
        elif isinstance(value, set):
            return "set"
        else:
            return type(value).__name__
    
    def _build_dependency_graph(
        self,
        app_contexts: List[Any],
    ) -> Dict[str, List[str]]:
        """
        Build dependency graph.
        
        Args:
            app_contexts: List of AppContext objects
            
        Returns:
            Adjacency dict
        """
        graph: Dict[str, List[str]] = {}
        
        for ctx in app_contexts:
            graph[ctx.name] = sorted(ctx.depends_on)
        
        return dict(sorted(graph.items()))
    
    def _canonicalize_dict(self, d: dict) -> Dict[str, Any]:
        """
        Canonicalize dict (sort keys, remove non-deterministic values).
        
        Args:
            d: Dict to canonicalize
            
        Returns:
            Canonical dict
        """
        result: Dict[str, Any] = {}
        
        for key in sorted(d.keys()):
            value = d[key]
            
            if isinstance(value, dict):
                result[key] = self._canonicalize_dict(value)
            elif isinstance(value, list):
                result[key] = [
                    self._canonicalize_dict(v) if isinstance(v, dict) else v
                    for v in value
                ]
            else:
                result[key] = value
        
        return result
    
    def generate_with_metadata(
        self,
        app_contexts: List[Any],
        config: Any,
        mode: Any,
    ) -> Dict[str, Any]:
        """
        Generate fingerprint with metadata.
        
        Args:
            app_contexts: List of AppContext objects
            config: Config object
            mode: RegistryMode
            
        Returns:
            Dict with fingerprint and metadata
        """
        from .core import RegistryFingerprint
        
        fingerprint_hash = self.generate(app_contexts, config, mode)
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # Count routes
        route_count = sum(len(ctx.controllers) for ctx in app_contexts)
        
        # Collect manifest sources
        manifest_sources = [
            getattr(ctx.manifest, "__source__", "unknown")
            for ctx in app_contexts
        ]
        
        return RegistryFingerprint(
            hash=fingerprint_hash,
            timestamp=timestamp,
            mode=mode.value,
            app_count=len(app_contexts),
            route_count=route_count,
            manifest_sources=manifest_sources,
        )
    
    def verify_fingerprint(
        self,
        expected: str,
        app_contexts: List[Any],
        config: Any,
        mode: Any,
    ) -> bool:
        """
        Verify current state matches expected fingerprint.
        
        Args:
            expected: Expected fingerprint hash
            app_contexts: List of AppContext objects
            config: Config object
            mode: RegistryMode
            
        Returns:
            True if matches, False otherwise
        """
        actual = self.generate(app_contexts, config, mode)
        return actual == expected
    
    def diff_fingerprints(
        self,
        expected_contexts: List[Any],
        actual_contexts: List[Any],
        config: Any,
        mode: Any,
    ) -> Dict[str, Any]:
        """
        Compute diff between expected and actual registry state.
        
        Args:
            expected_contexts: Expected app contexts
            actual_contexts: Actual app contexts
            config: Config object
            mode: RegistryMode
            
        Returns:
            Dict describing differences
        """
        expected_repr = self._build_canonical_repr(expected_contexts, config, mode)
        actual_repr = self._build_canonical_repr(actual_contexts, config, mode)
        
        diff: Dict[str, Any] = {}
        
        # Compare app counts
        if len(expected_contexts) != len(actual_contexts):
            diff["app_count"] = {
                "expected": len(expected_contexts),
                "actual": len(actual_contexts),
            }
        
        # Compare apps
        expected_apps = {ctx.name for ctx in expected_contexts}
        actual_apps = {ctx.name for ctx in actual_contexts}
        
        missing_apps = expected_apps - actual_apps
        extra_apps = actual_apps - expected_apps
        
        if missing_apps:
            diff["missing_apps"] = sorted(missing_apps)
        if extra_apps:
            diff["extra_apps"] = sorted(extra_apps)
        
        # Compare common apps
        common_apps = expected_apps & actual_apps
        app_diffs: Dict[str, Any] = {}
        
        for app_name in common_apps:
            expected_ctx = next(c for c in expected_contexts if c.name == app_name)
            actual_ctx = next(c for c in actual_contexts if c.name == app_name)
            
            app_diff = self._diff_app_contexts(expected_ctx, actual_ctx)
            if app_diff:
                app_diffs[app_name] = app_diff
        
        if app_diffs:
            diff["app_diffs"] = app_diffs
        
        return diff
    
    def _diff_app_contexts(self, expected: Any, actual: Any) -> Dict[str, Any]:
        """
        Diff two app contexts.
        
        Args:
            expected: Expected AppContext
            actual: Actual AppContext
            
        Returns:
            Dict describing differences
        """
        diff: Dict[str, Any] = {}
        
        if expected.version != actual.version:
            diff["version"] = {
                "expected": expected.version,
                "actual": actual.version,
            }
        
        expected_deps = set(expected.depends_on)
        actual_deps = set(actual.depends_on)
        
        if expected_deps != actual_deps:
            diff["depends_on"] = {
                "missing": sorted(expected_deps - actual_deps),
                "extra": sorted(actual_deps - expected_deps),
            }
        
        expected_controllers = set(expected.controllers)
        actual_controllers = set(actual.controllers)
        
        if expected_controllers != actual_controllers:
            diff["controllers"] = {
                "missing": sorted(expected_controllers - actual_controllers),
                "extra": sorted(actual_controllers - expected_controllers),
            }
        
        return diff
