"""
Config system - Layered typed configuration with validation.
Supports dataclass/pydantic-like behavior with merge precedence.
"""

from typing import Any, Dict, Optional, Type, get_type_hints, get_origin, get_args
from dataclasses import dataclass, fields, is_dataclass, MISSING
from pathlib import Path
import os
import json


class NestedNamespace:
    """
    A namespace that supports nested attribute access for app configs.
    Enables syntax like: config.apps.auth.secret_key
    """
    def __init__(self, data: Optional[Dict[str, Any]] = None):
        self._data = data or {}
    
    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            return object.__getattribute__(self, name)
        
        value = self._data.get(name)
        if isinstance(value, dict):
            return NestedNamespace(value)
        return value
    
    def __hasattr__(self, name: str) -> bool:
        return name in self._data
    
    def __getitem__(self, key: str) -> Any:
        return self._data[key]
    
    def __contains__(self, key: str) -> bool:
        return key in self._data
    
    def __dict__(self) -> dict:
        return self._data
    
    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)


class Config:
    """Base class for typed configuration classes."""
    pass


class ConfigError(Exception):
    """Raised when configuration validation fails."""
    pass


class ConfigLoader:
    """
    Loads and merges configuration from multiple sources with precedence:
    CLI args > Environment variables > .env files > config files > defaults
    """
    
    def __init__(self, env_prefix: str = "AQ_"):
        self.env_prefix = env_prefix
        self.config_data: Dict[str, Any] = {}
        self.apps = NestedNamespace()  # Add apps namespace
    
    @classmethod
    def load(
        cls,
        paths: Optional[list[str]] = None,
        env_prefix: str = "AQ_",
        env_file: Optional[str] = None,
        overrides: Optional[Dict[str, Any]] = None,
    ) -> "ConfigLoader":
        """
        Load configuration from multiple sources.
        
        Args:
            paths: List of config file paths (glob patterns supported)
            env_prefix: Prefix for environment variables
            env_file: Path to .env file
            overrides: Manual overrides (highest precedence)
            
        Returns:
            Configured ConfigLoader instance
        """
        loader = cls(env_prefix=env_prefix)
        
        # Load from files
        if paths:
            for pattern in paths:
                loader._load_from_files(pattern)
        
        # Load from .env file
        if env_file:
            loader._load_env_file(env_file)
        
        # Load from environment
        loader._load_from_env()
        
        # Apply overrides
        if overrides:
            loader._merge_dict(loader.config_data, overrides)
        
        # Build apps namespace
        loader._build_apps_namespace()
        
        return loader
    
    def _load_from_files(self, pattern: str):
        """Load config from Python or JSON files."""
        from glob import glob
        
        for path_str in glob(pattern):
            path = Path(path_str)
            
            if path.suffix == ".py":
                self._load_python_file(path)
            elif path.suffix == ".json":
                self._load_json_file(path)
    
    def _load_python_file(self, path: Path):
        """Load config from Python module."""
        import importlib.util
        
        spec = importlib.util.spec_from_file_location("config", path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Extract uppercase variables as config
            config = {
                key: value
                for key, value in vars(module).items()
                if key.isupper() and not key.startswith("_")
            }
            self._merge_dict(self.config_data, config)
    
    def _load_json_file(self, path: Path):
        """Load config from JSON file."""
        with open(path) as f:
            data = json.load(f)
            self._merge_dict(self.config_data, data)
    
    def _load_env_file(self, path: str):
        """Load config from .env file."""
        env_path = Path(path)
        if not env_path.exists():
            return
        
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                
                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    
                    if key.startswith(self.env_prefix):
                        self._set_nested(key, value)
    
    def _load_from_env(self):
        """Load config from environment variables."""
        for key, value in os.environ.items():
            if key.startswith(self.env_prefix):
                self._set_nested(key, value)
    
    def _set_nested(self, key: str, value: str):
        """Convert AQ_APPS_USERS_MAX_SIZE to nested dict."""
        # Remove prefix
        key = key[len(self.env_prefix):]
        
        # Split by double underscore for nested keys
        parts = key.lower().split("__")
        
        current = self.config_data
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        
        # Try to parse value
        current[parts[-1]] = self._parse_value(value)
    
    def _parse_value(self, value: str) -> Any:
        """Parse string value to appropriate type."""
        # Boolean
        if value.lower() in ("true", "yes", "1"):
            return True
        if value.lower() in ("false", "no", "0"):
            return False
        
        # Number
        try:
            if "." in value:
                return float(value)
            return int(value)
        except ValueError:
            pass
        
        # JSON
        if value.startswith(("{", "[")):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                pass
        
        return value
    
    def _merge_dict(self, target: dict, source: dict):
        """Deep merge source into target."""
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._merge_dict(target[key], value)
            else:
                target[key] = value
    
    def _build_apps_namespace(self):
        """Build nested namespace for apps from config_data['apps']."""
        apps_data = self.config_data.get("apps", {})
        self.apps = NestedNamespace(apps_data)
    
    def get(self, path: str, default: Any = None) -> Any:
        """Get config value by dot-separated path."""
        parts = path.split(".")
        current = self.config_data
        
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return default
        
        return current
    
    def get_app_config(self, app_name: str, config_class: Type[Config]) -> Config:
        """
        Get and validate configuration for a specific app.
        
        Args:
            app_name: Name of the app
            config_class: Config class to instantiate and validate
            
        Returns:
            Validated config instance
        """
        # Get app-specific config
        app_config_data = self.get(f"apps.{app_name}", {})
        
        # Also check root level
        root_data = {k: v for k, v in self.config_data.items() if k != "apps"}
        
        # Merge: app-specific overrides root
        merged = {**root_data, **app_config_data}
        
        # Instantiate and validate
        return self._instantiate_config(config_class, merged)
    
    def _instantiate_config(self, config_class: Type[Config], data: dict) -> Config:
        """Instantiate config class with validation."""
        if is_dataclass(config_class):
            return self._instantiate_dataclass(config_class, data)
        
        # For plain Config subclasses, create instance and set attributes
        instance = config_class()
        
        # Get type hints
        hints = get_type_hints(config_class)
        
        for key, value_type in hints.items():
            if key in data:
                value = data[key]
                # Basic type validation
                if not self._check_type(value, value_type):
                    raise ConfigError(
                        f"Config field '{key}' expected {value_type}, got {type(value)}"
                    )
                setattr(instance, key, value)
            elif hasattr(config_class, key):
                # Use default value
                default = getattr(config_class, key)
                setattr(instance, key, default)
        
        return instance
    
    def _instantiate_dataclass(self, config_class: Type, data: dict):
        """Instantiate dataclass config with validation."""
        kwargs = {}
        
        for field_info in fields(config_class):
            field_name = field_info.name
            field_type = field_info.type
            
            if field_name in data:
                value = data[field_name]
                
                # Validate type
                if not self._check_type(value, field_type):
                    raise ConfigError(
                        f"Config field '{field_name}' expected {field_type}, "
                        f"got {type(value).__name__}"
                    )
                
                kwargs[field_name] = value
            elif field_info.default is not MISSING:
                kwargs[field_name] = field_info.default
            elif field_info.default_factory is not MISSING:
                kwargs[field_name] = field_info.default_factory()
            else:
                raise ConfigError(
                    f"Required config field '{field_name}' not provided"
                )
        
        return config_class(**kwargs)
    
    def _check_type(self, value: Any, expected_type: Type) -> bool:
        """Basic type checking."""
        # Handle Optional types
        origin = get_origin(expected_type)
        if origin is type(Optional):
            args = get_args(expected_type)
            if value is None:
                return True
            if args:
                return self._check_type(value, args[0])
        
        # Handle generic types
        if origin:
            return isinstance(value, origin)
        
        # Direct type check
        try:
            return isinstance(value, expected_type)
        except TypeError:
            # For complex types, skip validation
            return True
    
    def to_dict(self) -> dict:
        """Export all config as dictionary."""
        return self.config_data.copy()
