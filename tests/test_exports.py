"""
Test 23: Framework Exports (aquilia/__init__.py)

Tests that all major public API symbols are importable from the top-level package.
"""

import pytest


class TestTopLevelExports:

    def test_request(self):
        from aquilia import Request
        assert Request is not None

    def test_response(self):
        from aquilia import Response
        assert Response is not None

    def test_controller(self):
        from aquilia import Controller
        assert Controller is not None

    def test_route_decorators(self):
        from aquilia import GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS
        assert GET is not None
        assert POST is not None
        assert PUT is not None
        assert PATCH is not None
        assert DELETE is not None
        assert HEAD is not None
        assert OPTIONS is not None

    def test_ws(self):
        from aquilia import WS
        assert WS is not None

    def test_flow_node(self):
        from aquilia.flow import FlowNode, FlowNodeType
        assert FlowNode is not None
        assert FlowNodeType is not None

    def test_di(self):
        from aquilia import Container, service, factory, inject
        assert Container is not None
        assert service is not None
        assert factory is not None
        assert inject is not None

    def test_effects(self):
        from aquilia import EffectRegistry
        assert EffectRegistry is not None

    def test_middleware(self):
        from aquilia import MiddlewareStack
        assert MiddlewareStack is not None

    def test_config(self):
        from aquilia import Config, ConfigLoader
        assert Config is not None
        assert ConfigLoader is not None

    def test_manifest(self):
        from aquilia import AppManifest
        assert AppManifest is not None

    def test_faults(self):
        from aquilia import Fault
        from aquilia.faults.core import FaultDomain, Severity
        assert Fault is not None
        assert FaultDomain is not None
        assert Severity is not None

    def test_sessions(self):
        from aquilia import Session
        assert Session is not None

    def test_auth(self):
        from aquilia import Identity, PasswordHasher
        assert Identity is not None
        assert PasswordHasher is not None

    def test_lifecycle(self):
        from aquilia import LifecycleCoordinator
        assert LifecycleCoordinator is not None

    def test_config_builders(self):
        from aquilia import Workspace, Module, Integration
        assert Workspace is not None
        assert Module is not None
        assert Integration is not None

    def test_aquilary(self):
        from aquilia import Aquilary
        assert Aquilary is not None

    def test_datastructures(self):
        from aquilia import MultiDict, Headers, URL
        assert MultiDict is not None
        assert Headers is not None
        assert URL is not None

    def test_upload_file(self):
        from aquilia import UploadFile
        assert UploadFile is not None

    def test_version(self):
        import aquilia
        assert hasattr(aquilia, "__version__")
