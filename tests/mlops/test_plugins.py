"""
Tests for aquilia.mlops.plugins - host, marketplace, example plugin.
"""

import json
from pathlib import Path

import pytest

from aquilia.mlops.plugins.host import PluginHost, PluginState
from aquilia.mlops.plugins.example_plugin import HealthCheckPlugin


class TestPluginHost:
    def test_register_instance(self):
        host = PluginHost()
        desc = host.register(HealthCheckPlugin())
        assert desc.name == "health-check"
        assert desc.version == "0.1.0"
        assert desc.state == PluginState.LOADED

    def test_register_class(self):
        host = PluginHost()
        desc = host.register(HealthCheckPlugin)
        assert desc.instance is not None
        assert desc.state == PluginState.LOADED
        assert desc.name == "health-check"

    def test_activate_deactivate(self):
        host = PluginHost()
        host.register(HealthCheckPlugin())
        host.activate("health-check", ctx={"host": host})
        desc = host.get("health-check")
        assert desc is not None
        assert desc.state == PluginState.ACTIVATED
        assert len(host.active_plugins) == 1
        host.deactivate("health-check")
        desc = host.get("health-check")
        assert desc.state == PluginState.DEACTIVATED
        assert len(host.active_plugins) == 0

    def test_list_plugins(self):
        host = PluginHost()
        host.register(HealthCheckPlugin())
        plugins = host.list_plugins()
        assert len(plugins) == 1

    def test_hook_events(self):
        host = PluginHost()
        results = []
        host.on("test_event", lambda msg="": results.append(msg))
        host.emit("test_event", msg="hello")
        assert results == ["hello"]

    def test_activate_nonexistent_raises(self):
        host = PluginHost()
        with pytest.raises(KeyError):
            host.activate("nonexistent")

    def test_activate_all(self):
        host = PluginHost()
        host.register(HealthCheckPlugin())
        host.activate_all(ctx={})
        assert len(host.active_plugins) == 1

    def test_deactivate_all(self):
        host = PluginHost()
        host.register(HealthCheckPlugin())
        host.activate_all(ctx={})
        host.deactivate_all()
        assert len(host.active_plugins) == 0


class TestHealthCheckPlugin:
    def test_stats(self):
        plugin = HealthCheckPlugin()
        plugin.activate({})
        plugin._on_inference(latency_ms=10.0)
        plugin._on_inference(latency_ms=20.0)
        plugin._on_inference(latency_ms=30.0)
        stats = plugin.stats()
        assert stats["inference_count"] == 3
        assert stats["avg_latency_ms"] == 20.0
        assert stats["uptime_s"] >= 0

    def test_integration_with_host(self):
        host = PluginHost()
        host.register(HealthCheckPlugin())
        host.activate("health-check", ctx={"host": host})
        host.emit("post_inference", latency_ms=15.0)
        host.emit("post_inference", latency_ms=25.0)
        desc = host.get("health-check")
        assert desc is not None
        assert desc.instance.stats()["inference_count"] == 2


class TestPluginMarketplace:
    async def test_search_from_file(self, tmp_path):
        from aquilia.mlops.plugins.marketplace import PluginMarketplace

        index = [
            {
                "name": "drift-monitor",
                "version": "1.0.0",
                "description": "Real-time drift monitoring",
                "author": "aquilia-team",
                "pypi_name": "aquilia-drift-monitor",
                "tags": ["drift", "monitoring"],
                "downloads": 1000,
                "verified": True,
            },
            {
                "name": "custom-runtime",
                "version": "0.5.0",
                "description": "Custom inference runtime",
                "author": "community",
                "pypi_name": "aquilia-custom-runtime",
                "tags": ["runtime"],
                "downloads": 200,
                "verified": False,
            },
        ]
        index_file = tmp_path / "index.json"
        index_file.write_text(json.dumps(index))

        mp = PluginMarketplace(index_url=str(index_file))
        await mp.fetch_index()
        results = mp.search("drift")
        assert len(results) == 1
        assert results[0].name == "drift-monitor"

        all_results = mp.search("", verified_only=True)
        assert len(all_results) == 1
