"""
Package Scanner Utility.

Provides robust runtime introspection to discover classes within modules
and packages. Essential for auto-discovery features.
"""

import importlib
import pkgutil
import inspect
import logging
from types import ModuleType
from typing import List, Type, Any, Optional, Callable, Set

logger = logging.getLogger("aquilia.scanner")


class PackageScanner:
    """
    Robust scanner for discovering classes in Python packages.
    
    Features:
    - Safe importing with error handling
    - Recursive package scanning
    - Class filtering (by type, name pattern, or predicate)
    - Deduplication
    """
    
    def __init__(self):
        self._scanned_modules: Set[str] = set()
    
    def scan_package(
        self,
        package_name: str,
        base_class: Optional[Type] = None,
        predicate: Optional[Callable[[Type], bool]] = None,
        recursive: bool = False,
    ) -> List[Type]:
        """
        Scan a package for classes matching criteria.
        
        Args:
            package_name: Dotted python path (e.g. 'myapp.modules.users.controllers')
            base_class: Optional base class to filter by (subclass check)
            predicate: Optional custom filter function
            recursive: Whether to scan subpackages (default False)
            
        Returns:
            List of discovered classes
        """
        discovered = []
        
        try:
            # Import the root module
            module = importlib.import_module(package_name)
            self._scan_module(module, discovered, base_class, predicate)
            
            if recursive and hasattr(module, "__path__"):
                for _, name, is_pkg in pkgutil.walk_packages(module.__path__, module.__name__ + "."):
                    try:
                        submodule = importlib.import_module(name)
                        self._scan_module(submodule, discovered, base_class, predicate)
                    except Exception as e:
                        logger.warning(f"Failed to scan submodule {name}: {e}")
                        
        except ImportError as e:
            logger.debug(f"Could not import package {package_name}: {e}")
            # Not an error, just means package doesn't exist (e.g. no controllers.py)
            return []
        except Exception as e:
            logger.error(f"Error scanning package {package_name}: {e}", exc_info=True)
            return []
            
        return discovered

    def _scan_module(
        self,
        module: ModuleType,
        discovered: List[Type],
        base_class: Optional[Type],
        predicate: Optional[Callable[[Type], bool]],
    ):
        """Internal helper to scan a single module."""
        try:
            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj):
                    # Filter by base class
                    if base_class and not issubclass(obj, base_class):
                        continue
                    
                    # Filter by predicate
                    if predicate and not predicate(obj):
                        continue
                    
                    # Avoid importing abstract base classes if possible?
                    # For now we include them, caller can filter if instance check fails
                    
                    # Ensure the class is defined in this module (or submodules)
                    # to avoid re-discovering imported classes from other libs
                    if hasattr(obj, "__module__") and obj.__module__.startswith(module.__package__ or ""):
                        if obj not in discovered:
                            discovered.append(obj)
                            
        except Exception as e:
            logger.warning(f"Error inspecting module {module.__name__}: {e}")
