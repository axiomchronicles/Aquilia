"""
Test suite for Aquilia core components.
"""

import pytest
from aquilia import AppManifest, Config, ConfigLoader, Registry
from aquilia.flow import flow, Flow
from aquilia.router import Router
from aquilia.di import DIContainer, ServiceScope


class TestConfig(Config):
    test_value: int = 42
    test_string: str = "hello"


class TestManifest:
    """Test manifest system."""
    
    def test_manifest_creation(self):
        """Test creating a manifest."""
        manifest = AppManifest(
            name="test",
            version="1.0.0",
        )
        
        assert manifest.name == "test"
        assert manifest.version == "1.0.0"
    
    def test_manifest_fingerprint(self):
        """Test manifest fingerprint generation."""
        manifest1 = AppManifest(
            name="test",
            version="1.0.0",
        )
        
        manifest2 = AppManifest(
            name="test",
            version="1.0.0",
        )
        
        # Same manifests should have same fingerprint
        assert manifest1.fingerprint() == manifest2.fingerprint()
        
        manifest3 = AppManifest(
            name="test",
            version="2.0.0",
        )
        
        # Different versions should have different fingerprints
        assert manifest1.fingerprint() != manifest3.fingerprint()


class TestConfigLoader:
    """Test configuration system."""
    
    def test_config_loading(self):
        """Test loading configuration."""
        loader = ConfigLoader.load(
            overrides={"test_key": "test_value"}
        )
        
        assert loader.get("test_key") == "test_value"
    
    def test_config_merging(self):
        """Test configuration merging."""
        loader = ConfigLoader()
        loader.config_data = {"a": 1, "b": {"c": 2}}
        
        loader._merge_dict(loader.config_data, {"b": {"d": 3}, "e": 4})
        
        assert loader.config_data == {
            "a": 1,
            "b": {"c": 2, "d": 3},
            "e": 4,
        }
    
    def test_nested_env_parsing(self):
        """Test nested environment variable parsing."""
        loader = ConfigLoader(env_prefix="TEST_")
        loader._set_nested("TEST_APP__DATABASE__HOST", "localhost")
        
        assert loader.config_data == {
            "app": {
                "database": {
                    "host": "localhost"
                }
            }
        }


class TestDIContainer:
    """Test dependency injection."""
    
    def test_singleton_registration(self):
        """Test singleton service registration."""
        container = DIContainer()
        
        class TestService:
            pass
        
        container.register(
            "TestService",
            TestService,
            scope=ServiceScope.SINGLETON,
        )
        
        assert "TestService" in container.descriptors
    
    @pytest.mark.asyncio
    async def test_service_resolution(self):
        """Test resolving services."""
        container = DIContainer()
        
        class TestService:
            def __init__(self):
                self.value = 42
        
        container.register("TestService", TestService)
        
        service = await container.resolve("TestService")
        assert service.value == 42
    
    @pytest.mark.asyncio
    async def test_dependency_injection(self):
        """Test dependency injection."""
        container = DIContainer()
        
        class DatabaseService:
            def __init__(self):
                self.connected = True
        
        class UserService:
            def __init__(self, DatabaseService):
                self.db = DatabaseService
        
        container.register("DatabaseService", DatabaseService)
        container.register("UserService", UserService)
        
        user_service = await container.resolve("UserService")
        assert user_service.db.connected


class TestFlow:
    """Test flow system."""
    
    def test_flow_creation(self):
        """Test creating a flow."""
        @flow("/test/{id}").GET
        async def test_handler(id: int):
            return {"id": id}
        
        assert hasattr(test_handler, "_aquilia_flow")
        flow_obj = test_handler._aquilia_flow
        
        assert flow_obj.pattern == "/test/{id}"
        assert flow_obj.method == "GET"
    
    def test_path_parsing(self):
        """Test path pattern parsing."""
        flow_obj = Flow("/users/{id}/posts/{post_id}")
        
        assert len(flow_obj.segments) == 4
        assert flow_obj.segments[0].type == "static"
        assert flow_obj.segments[1].type == "param"
        assert flow_obj.segments[1].param_name == "id"
    
    def test_path_matching(self):
        """Test path matching."""
        flow_obj = Flow("/users/{id}")
        
        params = flow_obj.matches("/users/123")
        assert params is not None
        assert params["id"] == "123"
        
        # Should not match different path
        params = flow_obj.matches("/posts/123")
        assert params is None


class TestRouter:
    """Test router."""
    
    def test_route_registration(self):
        """Test registering routes."""
        router = Router()
        
        @flow("/test").GET
        async def test_handler():
            return {}
        
        router.add_flow(test_handler._aquilia_flow)
        
        routes = router.get_routes()
        assert len(routes) == 1
        assert routes[0]["pattern"] == "/test"
    
    def test_route_matching(self):
        """Test route matching."""
        router = Router()
        
        @flow("/users/{id}").GET
        async def get_user(id: int):
            return {"id": id}
        
        router.add_flow(get_user._aquilia_flow)
        
        match = router.match("/users/42", "GET")
        assert match is not None
        assert match.params["id"] == 42
        
        # Should not match different method
        match = router.match("/users/42", "POST")
        assert match is None


class TestRegistry:
    """Test registry."""
    
    def test_registry_creation(self):
        """Test creating registry from manifests."""
        manifest = AppManifest(
            name="test",
            version="1.0.0",
        )
        
        registry = Registry.from_manifests([manifest])
        
        assert "test" in registry.apps
        assert len(registry.load_order) == 1
    
    def test_dependency_ordering(self):
        """Test dependency graph ordering."""
        app1 = AppManifest(name="app1", version="1.0.0", depends_on=[])
        app2 = AppManifest(name="app2", version="1.0.0", depends_on=["app1"])
        app3 = AppManifest(name="app3", version="1.0.0", depends_on=["app2"])
        
        registry = Registry.from_manifests([app3, app1, app2])
        
        # Should be ordered by dependencies
        assert registry.load_order == ["app1", "app2", "app3"]
    
    def test_circular_dependency_detection(self):
        """Test circular dependency detection."""
        app1 = AppManifest(name="app1", version="1.0.0", depends_on=["app2"])
        app2 = AppManifest(name="app2", version="1.0.0", depends_on=["app1"])
        
        with pytest.raises(Exception) as exc_info:
            Registry.from_manifests([app1, app2])
        
        assert "circular" in str(exc_info.value).lower()
    
    def test_fingerprint_generation(self):
        """Test registry fingerprint."""
        manifest = AppManifest(name="test", version="1.0.0")
        
        registry1 = Registry.from_manifests([manifest])
        registry2 = Registry.from_manifests([manifest])
        
        # Same manifests should produce same fingerprint
        assert registry1.fingerprint == registry2.fingerprint


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
