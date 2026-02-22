import pytest
import os
from pathlib import Path
from aquilia.config_builders import Workspace, Module, Integration
from aquilia.config import ConfigLoader


def test_config_builder_database_scan_dirs():
    """Test that Workspace configuration correctly propagates DatabaseConfig to the manifest loader."""
    
    workspace = (
        Workspace("test_db_workspace")
        .database(
            url="sqlite:///:memory:",
            scan_dirs=["custom_models"]
        )
        .module(
            Module("test_app")
        )
    )
    
    config_dict = workspace.to_dict()
    loader = ConfigLoader()
    loader._merge_dict(loader.config_data, config_dict)
    loader._build_apps_namespace()
    
    manifest_data = loader.config_data["modules"][0]
    if "database" in loader.config_data:
        # Simulate server merging workspace default database config into modules
        manifest_data["database"] = loader.config_data["database"]
    
    from aquilia.aquilary.loader import ManifestLoader
    manifest_loader = ManifestLoader()
    
    # Simulate loading from dict like in AquiliaServer
    manifest_cls = manifest_loader._dict_to_manifest(manifest_data, "config")
    manifest = manifest_loader.load_manifests([manifest_cls])[0]
    
    assert hasattr(manifest, "database")
    assert manifest.database is not None
    assert hasattr(manifest.database, "scan_dirs")
    assert "custom_models" in manifest.database.scan_dirs

