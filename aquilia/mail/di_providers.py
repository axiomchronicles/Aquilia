"""
AquilaMail — DI Providers

Dependency injection providers for the mail subsystem.
Enables proper lifecycle management and dependency resolution
following Aquilia's DI patterns (same as auth/integration/di_providers.py).

Provides:
- MailConfigProvider: resolves MailConfig from workspace config
- MailServiceProvider: resolves MailService with injected config
- MailProviderRegistry: auto-discovers IMailProvider implementations
- Factory functions for common configurations

Usage:
    The server._setup_mail() method registers these providers in the
    DI container so that MailService, MailConfig, and individual
    providers can be resolved via dependency injection.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from ..di.decorators import service, factory

if TYPE_CHECKING:
    from ..di import Container

logger = logging.getLogger("aquilia.mail.di")


# ============================================================================
# Config Provider
# ============================================================================


@service(scope="app", name="MailConfigProvider")
class MailConfigProvider:
    """
    DI provider that builds and validates MailConfig from workspace data.

    When resolved, returns a fully-validated MailConfig instance with
    all sub-configs run through their Serializers.
    """

    def __init__(self, config_data: Optional[Dict[str, Any]] = None):
        self._config_data = config_data or {}

    def provide(self) -> Any:
        """Provide validated MailConfig instance."""
        from .config import MailConfig

        if self._config_data:
            return MailConfig.from_dict(self._config_data)
        return MailConfig()


# ============================================================================
# Service Provider
# ============================================================================


@service(scope="app", name="MailServiceProvider")
class MailServiceProvider:
    """
    DI provider for MailService — the central mail orchestrator.

    Accepts a MailConfig (resolved from DI or provided directly)
    and produces a configured MailService singleton.
    """

    def __init__(self, config: Optional[Any] = None):
        self._config = config

    def provide(self) -> Any:
        """Provide MailService instance."""
        from .config import MailConfig
        from .service import MailService

        config = self._config
        if config is None:
            config = MailConfig()
        elif isinstance(config, dict):
            config = MailConfig.from_dict(config)

        return MailService(config=config)


# ============================================================================
# Provider Registry — Discovery-based
# ============================================================================


@service(scope="app", name="MailProviderRegistry")
class MailProviderRegistry:
    """
    Auto-discovers IMailProvider implementations using Aquilia's
    PackageScanner (discovery system).

    Scans:
    - ``aquilia.mail.providers`` (built-in providers)
    - User-specified packages (via config)

    This enables plugin-style mail providers — drop a module into your
    project's ``mail_providers/`` package and it's auto-discovered.
    """

    def __init__(self) -> None:
        self._discovered: Dict[str, type] = {}
        self._scan_packages: List[str] = ["aquilia.mail.providers"]

    def add_scan_package(self, package: str) -> None:
        """Add a package to scan for IMailProvider implementations."""
        if package not in self._scan_packages:
            self._scan_packages.append(package)

    def discover(self) -> Dict[str, type]:
        """
        Scan configured packages for IMailProvider implementations.

        Returns:
            Dict mapping provider type names to provider classes.
        """
        if self._discovered:
            return self._discovered

        try:
            from ..discovery import PackageScanner
            from .providers import IMailProvider

            scanner = PackageScanner()

            for package in self._scan_packages:
                try:
                    found = scanner.scan_package(
                        package_name=package,
                        predicate=lambda cls: (
                            hasattr(cls, "send")
                            and hasattr(cls, "initialize")
                            and hasattr(cls, "shutdown")
                            and cls is not IMailProvider
                        ),
                        recursive=True,
                        max_depth=2,
                    )
                    for cls in found:
                        # Use class name or a 'provider_type' attribute
                        ptype = getattr(cls, "provider_type", None)
                        if ptype is None:
                            ptype = cls.__name__.lower().replace("provider", "")
                        self._discovered[ptype] = cls
                        logger.debug(
                            f"Discovered mail provider: {ptype} → {cls.__qualname__}"
                        )
                except Exception as e:
                    logger.debug(f"Could not scan {package}: {e}")

        except ImportError:
            logger.debug("PackageScanner not available, skipping auto-discovery")

        return self._discovered

    def get_provider_class(self, provider_type: str) -> Optional[type]:
        """Get a discovered provider class by type name."""
        if not self._discovered:
            self.discover()
        return self._discovered.get(provider_type)

    def list_types(self) -> List[str]:
        """List all discovered provider type names."""
        if not self._discovered:
            self.discover()
        return list(self._discovered.keys())


# ============================================================================
# Factory functions
# ============================================================================


@factory(scope="app")
def create_mail_config(config_data: Optional[Dict[str, Any]] = None) -> Any:
    """
    Factory that creates a validated MailConfig.

    Can be registered in DI as::

        container.register(FactoryProvider(
            create_mail_config,
            scope="app",
        ))
    """
    from .config import MailConfig

    if config_data:
        return MailConfig.from_dict(config_data)
    return MailConfig()


@factory(scope="app")
def create_mail_service(config: Optional[Any] = None) -> Any:
    """
    Factory that creates a MailService from config.

    Can be registered in DI as::

        container.register(FactoryProvider(
            create_mail_service,
            scope="app",
        ))
    """
    from .config import MailConfig
    from .service import MailService

    if config is None:
        config = MailConfig()
    elif isinstance(config, dict):
        config = MailConfig.from_dict(config)
    return MailService(config=config)


# ============================================================================
# Registration helper
# ============================================================================


def register_mail_providers(
    container: "Container",
    config_data: Optional[Dict[str, Any]] = None,
    discover_providers: bool = True,
    extra_scan_packages: Optional[List[str]] = None,
) -> Any:
    """
    Register all mail DI providers into a container.

    This is called by ``AquiliaServer._setup_mail()`` to wire the full
    mail subsystem into the DI graph.

    Args:
        container: The DI container to register into.
        config_data: Raw mail config dict from workspace.
        discover_providers: Whether to auto-discover provider implementations.
        extra_scan_packages: Additional packages to scan for providers.

    Returns:
        The created MailService instance.
    """
    from ..di.providers import ValueProvider
    from .config import MailConfig
    from .service import MailService

    # 1. Build and validate config through serializers
    config_obj = MailConfig.from_dict(config_data or {})

    # 2. Create the service
    svc = MailService(config=config_obj)

    # 3. Register config in DI
    try:
        container.register(ValueProvider(
            value=config_obj,
            token=MailConfig,
            scope="app",
        ))
    except (ValueError, Exception):
        pass  # Already registered

    # 4. Register service in DI
    try:
        container.register(ValueProvider(
            value=svc,
            token=MailService,
            scope="app",
        ))
    except (ValueError, Exception):
        pass  # Already registered

    # 5. Auto-discover providers if requested
    if discover_providers:
        registry = MailProviderRegistry()
        if extra_scan_packages:
            for pkg in extra_scan_packages:
                registry.add_scan_package(pkg)
        registry.discover()

        try:
            container.register(ValueProvider(
                value=registry,
                token=MailProviderRegistry,
                scope="app",
            ))
        except (ValueError, Exception):
            pass

    return svc
