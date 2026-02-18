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
        
        if name not in self._data:
            raise AttributeError(f"'NestedNamespace' object has no attribute '{name}'")
            
        value = self._data.get(name)
        if isinstance(value, dict):
            return NestedNamespace(value)
        return value
    
    def __getitem__(self, key: str) -> Any:
        return self._data[key]
    
    def __contains__(self, key: str) -> bool:
        return key in self._data
    
    def to_dict(self) -> dict:
        """Return the underlying data dictionary."""
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
        Load configuration from multiple sources with proper merge strategy.
        
        Merge order (later overrides earlier):
        1. Workspace structure from aquilia.py (modules, integrations)
        2. Base config from config/base.yaml (shared defaults)
        3. Environment config from config/{mode}.yaml (dev, prod, etc.)
        4. Environment variables (AQ_* prefix)
        5. Manual overrides
        
        Supports both Python (aquilia.py) and YAML (aquilia.yaml) config files.
        Python files take precedence over YAML if both exist.
        
        Args:
            paths: List of config file paths (glob patterns supported)
            env_prefix: Prefix for environment variables
            env_file: Path to .env file
            overrides: Manual overrides (highest precedence)
            
        Returns:
            Configured ConfigLoader instance
        """
        loader = cls(env_prefix=env_prefix)
        
        # Step 1: Load workspace structure from aquilia.py or aquilia.yaml
        if not paths:
            # Auto-detect workspace config file
            if Path("aquilia.py").exists():
                paths = ["aquilia.py"]
            elif Path("aquilia.yaml").exists():
                paths = ["aquilia.yaml"]
        
        if paths:
            for pattern in paths:
                if pattern.endswith('.py'):
                    loader._load_python_config(pattern)
                else:
                    loader._load_from_files(pattern)
        
        # Step 2: Load base config (shared defaults)
        if Path("config/base.yaml").exists():
            loader._load_yaml_file(Path("config/base.yaml"))
        
        # Step 3: Load environment-specific config
        # Determine environment from workspace config or default to 'dev'
        mode = loader.config_data.get('runtime', {}).get('mode', 'dev')
        env_config_path = Path(f"config/{mode}.yaml")
        if env_config_path.exists():
            loader._load_yaml_file(env_config_path)
        
        # Step 4: Load from .env file
        if env_file:
            loader._load_env_file(env_file)
        
        # Step 5: Load from environment variables
        loader._load_from_env()
        
        # Step 6: Apply manual overrides
        if overrides:
            loader._merge_dict(loader.config_data, overrides)
        
        # Build apps namespace
        loader._build_apps_namespace()
        
        return loader
    
    def _load_python_config(self, path: str):
        """
        Load config from Python file (aquilia.py).
        
        Expects a 'workspace' variable that is a Workspace instance.
        """
        import importlib.util
        from pathlib import Path
        
        config_path = Path(path)
        if not config_path.exists():
            return
        
        # Load Python module
        spec = importlib.util.spec_from_file_location("aquilia_config", config_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Get workspace object
            if hasattr(module, 'workspace'):
                workspace = module.workspace
                # Convert workspace to dict and merge
                config_dict = workspace.to_dict()
                self._merge_dict(self.config_data, config_dict)
    
    def _load_from_files(self, pattern: str):
        """Load config from Python, JSON, or YAML files."""
        from glob import glob
        
        for path_str in glob(pattern):
            path = Path(path_str)
            
            if path.suffix == ".py":
                self._load_python_config(path)
            elif path.suffix == ".json":
                self._load_json_file(path)
            elif path.suffix in (".yaml", ".yml"):
                self._load_yaml_file(path)
    
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

    def _load_yaml_file(self, path: Path):
        """Load config from YAML file."""
        import yaml
        with open(path) as f:
            data = yaml.safe_load(f)
            if data:
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
        # Handle Optional types (Optional[X] is Union[X, None])
        import types
        origin = get_origin(expected_type)
        if origin is types.UnionType or str(origin) == 'typing.Union':
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
    
    def get_session_config(self) -> dict:
        """
        Get session configuration with defaults.
        
        Returns:
            Session configuration dictionary
        """
        default_session_config = {
            "enabled": False,  # Opt-in
            "policy": {
                "name": "user_default",
                "ttl_days": 7,
                "idle_timeout_minutes": 30,
                "rotate_on_privilege_change": True,
                "max_sessions_per_principal": 5,
            },
            "store": {
                "type": "memory",  # "memory", "file", "redis"
                "max_sessions": 10000,
                # File store options
                "directory": None,
                # Redis options (future)
                "redis_url": None,
                "key_prefix": "aquilia:session:",
            },
            "transport": {
                "adapter": "cookie",  # "cookie", "header"
                "cookie_name": "aquilia_session",
                "cookie_httponly": True,
                "cookie_secure": True,
                "cookie_samesite": "lax",
                "header_name": "X-Session-ID",
            },
        }
        
        # Get user-provided session config
        # Check multiple possible config paths for flexibility
        user_config = self.get("sessions", {})
        if not user_config:
            user_config = self.get("integrations.sessions", {})
        if not user_config:
            # Check if workspace config exists - the workspace puts sessions config directly at root level
            # when build() is called, so check there first
            pass
        
        # Merge with defaults
        merged = default_session_config.copy()
        if user_config:
            # Enable sessions if config provided
            merged["enabled"] = user_config.get("enabled", True)
            self._merge_dict(merged, user_config)
            
            # ── Normalize "store" field ──
            # YAML configs may specify store as a plain string (e.g., "memory")
            # instead of a dict (e.g., {"type": "memory", "max_sessions": 10000}).
            # Normalize to dict form so downstream code always gets a dict or object.
            if isinstance(merged.get("store"), str):
                store_str = merged["store"]
                merged["store"] = {
                    "type": store_str,
                    "max_sessions": 10000,
                }
            
            # Special handling for workspace policies - if policies list exists and contains SessionPolicy objects,
            # use the first one as the primary policy for the server
            if "policies" in user_config and user_config["policies"]:
                first_policy = user_config["policies"][0]
                # Check if it's a SessionPolicy object (from workspace), not just a string representation
                if hasattr(first_policy, 'name') and hasattr(first_policy, 'ttl'):
                    merged["policy"] = first_policy
                    # Also store reference to underlying transport/store if available
                    if hasattr(first_policy, 'transport'):
                        merged["transport_policy"] = first_policy.transport
        
        return merged
    
    def get_auth_config(self) -> dict:
        """
        Get auth configuration with defaults.
        
        Returns:
            Auth configuration dictionary
        """
        default_auth_config = {
            "enabled": False,  # Opt-in
            "store": {
                "type": "memory",  # "memory", "sql" (future)
                # SQL options
                "db_url": None,
            },
            "tokens": {
                "secret_key": "aquilia_insecure_dev_secret",  # Should be overridden in prod
                "algorithm": "HS256",
                "issuer": "aquilia",
                "audience": "aquilia-app",
                "access_token_ttl_minutes": 60,
                "refresh_token_ttl_days": 30,
            },
            "security": {
                "require_auth_by_default": False, # If true, all routes require auth unless public
                "hash_rounds": 12,
            }
        }
        
        # Get user-provided auth config
        user_config = self.get("auth", {})
        if not user_config:
            user_config = self.get("integrations.auth", {})
        
        # Merge with defaults
        merged = default_auth_config.copy()
        if user_config:
            merged["enabled"] = user_config.get("enabled", True)
            self._merge_dict(merged, user_config)
        
        return merged

    def get_template_config(self) -> dict:
        """
        Get template configuration with defaults.
        
        Returns:
            Template configuration dictionary
        """
        default_template_config = {
            "enabled": False,
            "search_paths": [],
            "precompile": False,
            "cache": "memory",  # "memory", "crous", "none"
            "sandbox": True,
            "sandbox_policy": "strict",
        }
        
        # Get user-provided template config
        user_config = self.get("templates", {})
        if not user_config:
            user_config = self.get("integrations.templates", {})
        
        # Merge with defaults
        merged = default_template_config.copy()
        if user_config:
            merged["enabled"] = user_config.get("enabled", True)
            self._merge_dict(merged, user_config)
        
        return merged

    def get_security_config(self) -> dict:
        """
        Get security configuration with defaults.

        Returns:
            Security configuration dictionary with middleware flags
        """
        default_security_config = {
            "enabled": False,
            "cors_enabled": False,
            "csrf_protection": False,
            "helmet_enabled": False,
            "rate_limiting": False,
            "https_redirect": False,
            "hsts": False,
            "proxy_fix": False,
        }

        user_config = self.get("security", {})

        merged = default_security_config.copy()
        if user_config:
            merged["enabled"] = user_config.get("enabled", True)
            self._merge_dict(merged, user_config)

        return merged

    def get_static_config(self) -> dict:
        """
        Get static files configuration with defaults.

        Returns:
            Static files configuration dictionary
        """
        default_static_config = {
            "enabled": False,
            "directories": {"/static": "static"},
            "cache_max_age": 86400,
            "etag": True,
            "gzip": True,
            "brotli": True,
            "memory_cache": True,
        }

        user_config = self.get("integrations.static_files", {})
        if not user_config:
            user_config = self.get("static_files", {})

        merged = default_static_config.copy()
        if user_config:
            merged["enabled"] = user_config.get("enabled", True)
            self._merge_dict(merged, user_config)

        return merged

    def get_cache_config(self) -> dict:
        """
        Get cache configuration with defaults.

        Returns:
            Cache configuration dictionary
        """
        default_cache_config = {
            "enabled": False,
            "backend": "memory",
            "default_ttl": 300,
            "max_size": 10000,
            "eviction_policy": "lru",
            "namespace": "default",
            "key_prefix": "aq:",
            "serializer": "json",
            "redis_url": "redis://localhost:6379/0",
            "redis_max_connections": 10,
            "redis_socket_timeout": 5.0,
            "redis_socket_connect_timeout": 5.0,
            "redis_retry_on_timeout": True,
            "redis_decode_responses": True,
            "l1_max_size": 1000,
            "l1_ttl": 60,
            "l2_backend": "redis",
            "middleware_enabled": False,
            "middleware_cacheable_methods": ["GET", "HEAD"],
            "middleware_default_ttl": 60,
            "middleware_vary_headers": ["Accept", "Accept-Encoding"],
            "trace_enabled": True,
            "metrics_enabled": True,
            "log_level": "WARNING",
        }

        # Get user-provided cache config
        user_config = self.get("cache", {})
        if not user_config:
            user_config = self.get("integrations.cache", {})

        # Merge with defaults
        merged = default_cache_config.copy()
        if user_config:
            merged["enabled"] = user_config.get("enabled", True)
            self._merge_dict(merged, user_config)

        return merged

    def get_mail_config(self) -> dict:
        """
        Get mail configuration with defaults.

        Returns:
            Mail configuration dictionary
        """
        default_mail_config = {
            "enabled": False,
            "default_from": "noreply@localhost",
            "default_reply_to": None,
            "subject_prefix": "",
            "providers": [],
            "console_backend": False,
            "preview_mode": False,
            "templates": {
                "template_dirs": ["mail_templates"],
                "auto_escape": True,
                "cache_compiled": True,
                "strict_mode": False,
            },
            "retry": {
                "max_attempts": 5,
                "base_delay": 1.0,
                "max_delay": 3600.0,
                "jitter": True,
            },
            "rate_limit": {
                "global_per_minute": 1000,
                "per_domain_per_minute": 100,
            },
            "security": {
                "dkim_enabled": False,
                "require_tls": True,
                "pii_redaction_enabled": False,
            },
            "metrics_enabled": True,
            "tracing_enabled": False,
        }

        # Get user-provided mail config
        user_config = self.get("mail", {})
        if not user_config:
            user_config = self.get("integrations.mail", {})

        # Merge with defaults
        merged = default_mail_config.copy()
        if user_config:
            merged["enabled"] = user_config.get("enabled", True)
            self._merge_dict(merged, user_config)

        return merged


