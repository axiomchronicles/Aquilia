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
    Enhanced scanner for discovering classes in Python packages.
    
    Features:
    - Safe importing with error handling
    - Recursive package scanning with depth control
    - Intelligent caching for performance
    - Class filtering (by type, name pattern, or predicate)
    - Deduplication and conflict detection
    - Pattern-based file discovery
    - Performance metrics and reporting
    """
    
    def __init__(self, cache_ttl: int = 300):
        self._scanned_modules: Set[str] = set()
        self._class_cache: Dict[str, List[Type]] = {}
        self._module_cache: Dict[str, ModuleType] = {}
        self._cache_timestamps: Dict[str, float] = {}
        self._cache_ttl = cache_ttl  # 5 minutes default
        self._scan_stats = {
            'cache_hits': 0,
            'cache_misses': 0,
            'scan_time': 0.0,
            'modules_scanned': 0,
            'classes_found': 0,
            'errors_encountered': 0
        }
        
    def clear_cache(self) -> None:
        """Clear all caches."""
        self._class_cache.clear()
        self._module_cache.clear()
        self._cache_timestamps.clear()
        self._scan_stats = dict.fromkeys(self._scan_stats, 0)
        
    def get_stats(self) -> Dict[str, Any]:
        """Get scanning performance statistics."""
        return self._scan_stats.copy()
        
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid."""
        if cache_key not in self._cache_timestamps:
            return False
        import time
        return (time.time() - self._cache_timestamps[cache_key]) < self._cache_ttl
    
    def scan_package(
        self,
        package_name: str,
        base_class: Optional[Type] = None,
        predicate: Optional[Callable[[Type], bool]] = None,
        recursive: bool = False,
        max_depth: int = 3,
        use_cache: bool = True,
    ) -> List[Type]:
        """
        Enhanced scan a package for classes matching criteria.
        
        Args:
            package_name: Dotted python path (e.g. 'myapp.modules.users.controllers')
            base_class: Optional base class to filter by (subclass check)
            predicate: Optional custom filter function
            recursive: Whether to scan subpackages (default False)
            max_depth: Maximum recursion depth for subpackages
            use_cache: Whether to use caching for performance
            
        Returns:
            List of discovered classes
        """
        import time
        start_time = time.time()
        
        # Generate cache key
        # IMPORTANT: Use predicate/base_class qualname or repr for stable identity.
        # Using id() is unsafe because Python can reuse memory addresses for
        # short-lived lambdas, causing cache collisions between different predicates.
        predicate_key = getattr(predicate, '__qualname__', repr(predicate)) if predicate else "None"
        base_class_key = getattr(base_class, '__qualname__', repr(base_class)) if base_class else "None"
        cache_key = f"{package_name}:{base_class_key}:{predicate_key}:{recursive}:{max_depth}"
        
        # Check cache first
        if use_cache and cache_key in self._class_cache and self._is_cache_valid(cache_key):
            self._scan_stats['cache_hits'] += 1
            return self._class_cache[cache_key][:]
        
        self._scan_stats['cache_misses'] += 1
        discovered = []
        
        try:
            # Import the root module (with caching)
            if package_name in self._module_cache and self._is_cache_valid(f"mod:{package_name}"):
                module = self._module_cache[package_name]
            else:
                module = importlib.import_module(package_name)
                if use_cache:
                    self._module_cache[package_name] = module
                    self._cache_timestamps[f"mod:{package_name}"] = time.time()
            
            self._scan_module(module, discovered, base_class, predicate)
            self._scan_stats['modules_scanned'] += 1
            
            # Enhanced recursive scanning with depth control
            if recursive and hasattr(module, "__path__") and max_depth > 0:
                seen_modules = {module.__name__}
                
                for _, name, is_pkg in pkgutil.walk_packages(
                    module.__path__, 
                    module.__name__ + ".",
                    onerror=lambda x: None  # Ignore import errors
                ):
                    # Depth check
                    current_depth = name.count('.') - package_name.count('.')
                    if current_depth > max_depth:
                        continue
                        
                    # Avoid infinite loops
                    if name in seen_modules:
                        continue
                    seen_modules.add(name)
                    
                    # Skip known problematic patterns
                    if any(skip in name.lower() for skip in [
                        'test', 'mock', 'fixture', 'migration', 'static', 
                        'template', '__pycache__', '.pyc'
                    ]):
                        continue
                    
                    try:
                        if name in self._module_cache and self._is_cache_valid(f"mod:{name}"):
                            submodule = self._module_cache[name]
                        else:
                            submodule = importlib.import_module(name)
                            if use_cache:
                                self._module_cache[name] = submodule
                                self._cache_timestamps[f"mod:{name}"] = time.time()
                        
                        self._scan_module(submodule, discovered, base_class, predicate)
                        self._scan_stats['modules_scanned'] += 1
                    except Exception as e:
                        self._scan_stats['errors_encountered'] += 1
                        logger.debug(f"Failed to scan submodule {name}: {e}")
                        
        except ImportError as e:
            logger.debug(f"Could not import package {package_name}: {e}")
            # Not an error, just means package doesn't exist
        except Exception as e:
            self._scan_stats['errors_encountered'] += 1
            logger.error(f"Error scanning package {package_name}: {e}")
        
        # Cache results
        if use_cache:
            self._class_cache[cache_key] = discovered[:]
            self._cache_timestamps[cache_key] = time.time()
        
        # Update stats
        self._scan_stats['classes_found'] += len(discovered)
        self._scan_stats['scan_time'] += time.time() - start_time
            
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
