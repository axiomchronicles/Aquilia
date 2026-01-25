"""
Enhanced discovery utilities for Aquilia CLI.

This module provides intelligent classification and filtering for discovered
controllers and services, with proper type detection and deduplication.
"""

import importlib
import re
from pathlib import Path
from typing import List, Dict, Set, Tuple, Optional, Type
from aquilia.utils.scanner import PackageScanner


class TypeClassifier:
    """Classifies discovered classes as controllers, services, or other."""
    
    @staticmethod
    def is_controller_class(cls: Type) -> bool:
        """
        Determine if a class is a controller.
        
        Args:
            cls: Class to check
            
        Returns:
            True if class is a controller
        """
        # MUST NOT be a service
        if cls.__name__.endswith(("Service", "Provider", "Repository", "DAO", "Manager")):
            return False
        
        # Check if it inherits from Controller base class
        try:
            from aquilia import Controller
            if issubclass(cls, Controller):
                return True
        except (ImportError, TypeError):
            pass
        
        # Check class name patterns
        if cls.__name__.endswith(("Controller", "Handler", "View")):
            return True
        
        # Check for controller markers
        if hasattr(cls, 'prefix') and not hasattr(cls, '__di_scope__'):
            return True
        if hasattr(cls, '__controller_routes__'):
            return True
        
        # Check for HTTP method attributes (duck typing)
        http_methods = ['get', 'post', 'put', 'delete', 'patch', 'options', 'head']
        if any(hasattr(cls, method) for method in http_methods):
            return True
        
        # Check for route attributes (Express/FastAPI style)
        if any(attr.startswith('route_') for attr in dir(cls)):
            return True
        
        return False
    
    @staticmethod
    def is_service_class(cls: Type) -> bool:
        """
        Determine if a class is a service/provider.
        
        Args:
            cls: Class to check
            
        Returns:
            True if class is a service
        """
        # Check for @service decorator markers
        # The @service decorator from aquilia.di sets __di_scope__
        if hasattr(cls, '__di_scope__'):
            return True
        if hasattr(cls, '__service_name__'):
            return True
        if hasattr(cls, '__injectable__'):
            return True
        
        # Check class name patterns ONLY if not a controller
        if cls.__name__.endswith(("Service", "Provider", "Repository", "DAO", "Manager")):
            # But verify it's not actually a controller (Controller subclass)
            try:
                from aquilia import Controller
                if not issubclass(cls, Controller):
                    return True
            except (ImportError, TypeError):
                return True
        
        # Check for service-specific markers in class dict
        if '__annotations__' in cls.__dict__:
            # Services often have dependency annotations
            pass
        
        return False
    
    @staticmethod
    def classify(cls: Type) -> Optional[str]:
        """
        Classify a discovered class.
        
        Returns:
            "controller", "service", or None if unclassifiable
        """
        is_ctrl = TypeClassifier.is_controller_class(cls)
        is_svc = TypeClassifier.is_service_class(cls)
        
        # If both match, prefer more specific: service patterns are more specific
        if is_svc:
            return "service"
        elif is_ctrl:
            return "controller"
        
        return None


class EnhancedDiscovery:
    """Enhanced discovery with intelligent classification and filtering."""
    
    def __init__(self, verbose: bool = False):
        self.scanner = PackageScanner()
        self.verbose = verbose
        self._discovered_cache: Dict[str, Tuple[str, Type]] = {}
    
    def discover_module_controllers_and_services(
        self,
        base_package: str,
        module_name: str,
    ) -> Tuple[List[str], List[str]]:
        """
        Discover controllers and services in a module with intelligent classification.
        
        Robust discovery that handles:
        - Missing modules gracefully
        - Import errors without crashing
        - Circular dependencies
        - Partial module loads
        - Invalid class definitions
        
        Args:
            base_package: Base package path (e.g., "modules.mymodule")
            module_name: Module name (e.g., "mymodule")
            
        Returns:
            Tuple of (controllers_list, services_list) with full module paths
        """
        all_discovered: Dict[str, Tuple[str, Type]] = {}  # key -> (type, class)
        
        try:
            # Import the base module to get its path
            module_package = importlib.import_module(base_package)
            if not hasattr(module_package, '__path__'):
                return [], []
            
            module_dir = Path(module_package.__path__[0])
        except (ImportError, AttributeError, ValueError) as e:
            if self.verbose:
                print(f"    ⚠️  Cannot import base package {base_package}: {str(e)[:60]}")
            return [], []
        
        # Strategy 1: Scan standard package locations
        standard_packages = [
            ("controllers", "controller"),
            ("services", "service"),
            ("handlers", "controller"),
            ("providers", "service"),
            ("repositories", "service"),
        ]
        
        for pkg_name, expected_type in standard_packages:
            location = f"{base_package}.{pkg_name}"
            try:
                classes = self.scanner.scan_package(
                    location,
                    predicate=lambda cls: True,  # Get all classes, classify later
                )
                for cls in classes:
                    try:
                        classification = TypeClassifier.classify(cls)
                        # Only keep if classified as expected type (controllers in controllers package, etc)
                        # This prevents importing cross-module classes
                        if classification == expected_type:
                            key = f"{cls.__module__}:{cls.__name__}"
                            if key not in all_discovered:
                                all_discovered[key] = (classification, cls)
                            if self.verbose and classification:
                                print(f"    ✓ {pkg_name}: {cls.__name__} ({classification})")
                    except Exception as e:
                        if self.verbose:
                            print(f"    ⚠️  Error classifying {cls.__name__}: {str(e)[:40]}")
            except (ImportError, ModuleNotFoundError, ValueError):
                pass  # Package doesn't exist, skip it
            except Exception as e:
                if self.verbose:
                    print(f"    ⚠️  Error scanning package {location}: {str(e)[:50]}")
        
        # Strategy 2: Scan individual files with intelligent detection
        try:
            if not module_dir.exists():
                return [], []
            
            controller_patterns = [
                "*controller*.py", "*ctrl*.py", "*handler*.py",
                "*view*.py", "*route*.py", "*api*.py",
            ]
            service_patterns = [
                "*service*.py", "*provider*.py", "*repository*.py",
                "*repo*.py", "*dao*.py", "*manager*.py",
            ]
            
            # Collect candidate files
            controller_files = set()
            service_files = set()
            
            try:
                for pattern in controller_patterns:
                    controller_files.update(module_dir.glob(pattern))
                for pattern in service_patterns:
                    service_files.update(module_dir.glob(pattern))
            except OSError as e:
                if self.verbose:
                    print(f"    ⚠️  Error scanning files: {str(e)[:50]}")
                return list(all_discovered.values())  # Return what we found so far
            
            # All Python files (for fallback)
            try:
                all_py_files = set(module_dir.glob("*.py"))
            except OSError:
                all_py_files = set()
            
            exclude_files = {
                module_dir / "__init__.py",
                module_dir / "manifest.py",
                module_dir / "config.py",
                module_dir / "settings.py",
                module_dir / "faults.py",
                module_dir / "middleware.py",
            }
            other_files = all_py_files - controller_files - service_files - exclude_files
            
            # Process files in priority order with type hints
            for py_file in sorted(controller_files):
                if py_file.stem in ['__init__', 'manifest', 'config', 'settings', 'faults', 'middleware']:
                    continue
                
                if not py_file.exists():
                    continue
                
                submodule_name = f"{base_package}.{py_file.stem}"
                
                try:
                    # Quick content check for performance
                    try:
                        content = py_file.read_text(encoding='utf-8', errors='ignore')
                    except (OSError, IOError) as e:
                        if self.verbose:
                            print(f"    ⚠️  Cannot read {py_file.name}: {str(e)[:40]}")
                        continue
                    
                    if not ('class ' in content):
                        continue
                    
                    # Scan the file
                    try:
                        classes = self.scanner.scan_package(submodule_name, predicate=lambda cls: True)
                    except (ImportError, SyntaxError, ValueError, ModuleNotFoundError) as e:
                        if self.verbose:
                            print(f"    ⚠️  Cannot import {py_file.name}: {str(e)[:50]}")
                        continue
                    
                    for cls in classes:
                        try:
                            # Skip standard library and built-in classes
                            if cls.__module__.startswith(('builtins', '__builtin__', 'typing')):
                                continue
                            
                            classification = TypeClassifier.classify(cls)
                            # Only keep controllers from controller files
                            if classification == "controller":
                                key = f"{cls.__module__}:{cls.__name__}"
                                if key not in all_discovered:
                                    all_discovered[key] = (classification, cls)
                                if self.verbose:
                                    print(f"    ✓ {py_file.name}: {cls.__name__} ({classification})")
                        except Exception as e:
                            if self.verbose:
                                print(f"    ⚠️  Error processing {cls.__name__}: {str(e)[:40]}")
                except Exception as e:
                    if self.verbose:
                        print(f"    ⚠️  Error scanning {py_file.name}: {str(e)[:50]}")
            
            # Service files
            for py_file in sorted(service_files):
                if py_file.stem in ['__init__', 'manifest', 'config', 'settings', 'faults', 'middleware']:
                    continue
                
                if not py_file.exists():
                    continue
                
                submodule_name = f"{base_package}.{py_file.stem}"
                
                try:
                    try:
                        content = py_file.read_text(encoding='utf-8', errors='ignore')
                    except (OSError, IOError):
                        continue
                    
                    if not ('class ' in content):
                        continue
                    
                    try:
                        classes = self.scanner.scan_package(submodule_name, predicate=lambda cls: True)
                    except (ImportError, SyntaxError, ValueError, ModuleNotFoundError):
                        continue
                    
                    for cls in classes:
                        try:
                            if cls.__module__.startswith(('builtins', '__builtin__', 'typing')):
                                continue
                            
                            classification = TypeClassifier.classify(cls)
                            # Only keep services from service files
                            if classification == "service":
                                key = f"{cls.__module__}:{cls.__name__}"
                                if key not in all_discovered:
                                    all_discovered[key] = (classification, cls)
                                if self.verbose:
                                    print(f"    ✓ {py_file.name}: {cls.__name__} ({classification})")
                        except Exception as e:
                            if self.verbose:
                                print(f"    ⚠️  Error processing {cls.__name__}: {str(e)[:40]}")
                except Exception as e:
                    if self.verbose:
                        print(f"    ⚠️  Error scanning {py_file.name}: {str(e)[:50]}")
            
            # Other files - classify based on actual type
            for py_file in sorted(other_files):
                if py_file.stem in ['__init__', 'manifest', 'config', 'settings', 'faults', 'middleware']:
                    continue
                
                if not py_file.exists():
                    continue
                
                submodule_name = f"{base_package}.{py_file.stem}"
                
                try:
                    try:
                        content = py_file.read_text(encoding='utf-8', errors='ignore')
                    except (OSError, IOError):
                        continue
                    
                    if not ('class ' in content):
                        continue
                    
                    try:
                        classes = self.scanner.scan_package(submodule_name, predicate=lambda cls: True)
                    except (ImportError, SyntaxError, ValueError, ModuleNotFoundError):
                        continue
                    
                    for cls in classes:
                        try:
                            if cls.__module__.startswith(('builtins', '__builtin__', 'typing')):
                                continue
                            
                            classification = TypeClassifier.classify(cls)
                            if classification:
                                key = f"{cls.__module__}:{cls.__name__}"
                                if key not in all_discovered:
                                    all_discovered[key] = (classification, cls)
                                if self.verbose:
                                    print(f"    ✓ {py_file.name}: {cls.__name__} ({classification})")
                        except Exception as e:
                            if self.verbose:
                                print(f"    ⚠️  Error processing {cls.__name__}: {str(e)[:40]}")
                except Exception as e:
                    if self.verbose:
                        print(f"    ⚠️  Error scanning {py_file.name}: {str(e)[:50]}")
        
        except Exception as e:
            if self.verbose:
                print(f"    ⚠️  Unexpected error in file scanning: {str(e)[:60]}")
        
        # Extract and return discovered items
        controllers_list = []
        services_list = []
        
        for key, (classification, cls) in all_discovered.items():
            if classification == "controller":
                controllers_list.append(key)
            elif classification == "service":
                services_list.append(key)
        
        return sorted(controllers_list), sorted(services_list)
    
    def clean_manifest_lists(
        self,
        manifest_content: str,
        discovered_controllers: List[str],
        discovered_services: List[str],
        module_dir: Optional[Path] = None,
    ) -> Tuple[str, int, int]:
        """
        Clean and update manifest.py with properly classified items.
        
        Robustness features:
        - Validates that all registered items actually exist (handle deleted files)
        - Deduplicates entries
        - Fixes misclassified items (services in controllers list)
        - Handles malformed manifest entries
        - Preserves order for consistency
        
        Args:
            manifest_content: Current manifest.py content
            discovered_controllers: Newly discovered controllers
            discovered_services: Newly discovered services
            module_dir: Path to the module directory for validation
            
        Returns:
            Tuple of (updated_content, services_added, controllers_added)
        """
        # Extract current declarations
        current_services = self._extract_list_from_manifest(manifest_content, "services=")
        current_controllers = self._extract_list_from_manifest(manifest_content, "controllers=")
        
        # Deduplicate discovered items
        discovered_controllers = sorted(list(set(discovered_controllers)))
        discovered_services = sorted(list(set(discovered_services)))
        
        # Validate that all registered items actually exist (handle deleted files)
        valid_controllers = self._validate_imports(current_controllers, module_dir)
        valid_services = self._validate_imports(current_services, module_dir)
        
        # Deduplicate validated items
        valid_controllers = sorted(list(set(valid_controllers)))
        valid_services = sorted(list(set(valid_services)))
        
        # Identify mislassified items in current controllers list
        # (services that were incorrectly put in controllers)
        misclassified_services = []
        properly_classified_controllers = []
        
        for item in valid_controllers:
            # Check if this looks like a service based on naming patterns
            if any(pattern in item for pattern in ['Service', 'Provider', 'Repository', 'DAO', 'Manager']):
                # This looks like a service, move it
                if item not in valid_services and item not in discovered_services:
                    misclassified_services.append(item)
            else:
                properly_classified_controllers.append(item)
        
        # Merge with discovered items (discovered takes priority to ensure fresh discovery)
        # Use sets to avoid duplicates, then sort for consistency
        final_services = sorted(list(set(
            valid_services + discovered_services + misclassified_services
        )))
        final_controllers = sorted(list(set(
            properly_classified_controllers + discovered_controllers
        )))
        
        # Remove any services from controllers list (cleanup)
        final_controllers = [c for c in final_controllers if not any(
            pattern in c for pattern in ['Service', 'Provider', 'Repository', 'DAO']
        )]
        
        # Sort for consistency
        final_services.sort()
        final_controllers.sort()
        
        # Calculate changes
        services_added = len([s for s in final_services if s not in current_services])
        controllers_added = len([c for c in final_controllers if c not in current_controllers])
        
        # Update manifest content
        updated_content = manifest_content
        
        if final_services != current_services:
            old_block = self._extract_services_block(manifest_content)
            new_block = self._generate_services_block(final_services)
            if old_block:
                updated_content = updated_content.replace(old_block, new_block)
        
        if final_controllers != current_controllers:
            old_block = self._extract_controllers_block(manifest_content)
            new_block = self._generate_controllers_block(final_controllers)
            if old_block:
                updated_content = updated_content.replace(old_block, new_block)
        
        return updated_content, services_added, controllers_added
    
    @staticmethod
    def _extract_list_from_manifest(content: str, key: str) -> List[str]:
        """Extract list items from manifest.py, ignoring commented lines."""
        try:
            pattern = rf'{re.escape(key)}\s*\[(.*?)\]'
            match = re.search(pattern, content, re.DOTALL)
            if not match:
                return []
            
            list_content = match.group(1)
            
            # Process line by line to exclude comments
            items = []
            for line in list_content.split('\n'):
                # Strip whitespace
                stripped = line.strip()
                
                # Skip empty lines and comments
                if not stripped or stripped.startswith('#'):
                    continue
                
                # Extract quoted strings from this line
                quoted_items = re.findall(r'"([^"]*)"', line)
                items.extend(quoted_items)
            
            return items
        except Exception:
            return []
    
    @staticmethod
    def _validate_imports(items: List[str], module_dir: Optional[Path]) -> List[str]:
        """
        Validate that imported items can still be imported (files exist).
        Remove any items whose files have been deleted.
        
        Robustness features:
        - Handles malformed import paths gracefully
        - Validates file existence
        - Deduplicates entries
        - Handles path resolution errors
        
        Args:
            items: List of import paths like "modules.mymodule.controllers:MyClass"
            module_dir: Path to the module directory for validation
            
        Returns:
            Filtered and deduplicated list with only valid imports
        """
        if not module_dir:
            # If no module dir provided, just deduplicate and return
            return sorted(list(set(items)))
        
        valid_items = []
        seen_imports = set()  # Track what we've already added
        
        for item in items:
            # Skip duplicates
            if item in seen_imports:
                continue
            
            # Validate import format
            if not item or ':' not in item:
                # Invalid format, skip it
                continue
            
            try:
                module_path, class_name = item.split(':', 1)
                
                # Validate module_path format
                if not module_path or not class_name:
                    continue
                
                # Skip empty/invalid class names
                if not class_name.replace('_', '').replace('0123456789', '').isalpha():
                    if not (class_name[0].isalpha() or class_name[0] == '_'):
                        continue
                
                # Convert module path to file path
                # "modules.mymodule.controllers" -> "modules/mymodule/controllers.py"
                parts = module_path.split('.')
                
                # Validate we have the right structure
                if len(parts) < 2:
                    continue
                
                # Find the file - start from module_dir
                try:
                    file_path = module_dir
                    for part in parts[1:]:  # Skip 'modules' prefix
                        file_path = file_path / part
                    
                    # Resolve symlinks and handle path issues
                    file_path = file_path.with_suffix('.py')
                    
                    # Check if file exists
                    if file_path.exists():
                        valid_items.append(item)
                        seen_imports.add(item)
                    # else: File was deleted, silently skip it
                except (OSError, ValueError, TypeError):
                    # Path resolution failed, skip this item
                    pass
                    
            except (ValueError, AttributeError, TypeError):
                # Malformed import string, skip it
                pass
        
        return sorted(list(set(valid_items)))  # Final deduplication and sort
    
    @staticmethod
    def _extract_services_block(content: str) -> str:
        """Extract the services=[ ... ] block from manifest."""
        pattern = r'#\s*Services with detailed DI configuration\s*\n\s*services=\s*\[(.*?)\],\s*\n'
        match = re.search(pattern, content, re.DOTALL)
        if match:
            return match.group(0)
        return ""
    
    @staticmethod
    def _extract_controllers_block(content: str) -> str:
        """Extract the controllers=[ ... ] block from manifest."""
        pattern = r'#\s*Controllers with routing\s*\n\s*controllers=\s*\[(.*?)\],\s*\n'
        match = re.search(pattern, content, re.DOTALL)
        if match:
            return match.group(0)
        return ""
    
    @staticmethod
    def _generate_services_block(services: List[str]) -> str:
        """Generate the services=[ ... ] block for manifest."""
        if not services:
            return '    # Services with detailed DI configuration\n    services=[],\n'
        
        items = ",\n        ".join(f'"{s}"' for s in services)
        return f'''    # Services with detailed DI configuration
    services=[
        {items},
    ],
'''
    
    @staticmethod
    def _generate_controllers_block(controllers: List[str]) -> str:
        """Generate the controllers=[ ... ] block for manifest."""
        if not controllers:
            return '    # Controllers with routing\n    controllers=[],\n'
        
        items = ",\n        ".join(f'"{c}"' for c in controllers)
        return f'''    # Controllers with routing
    controllers=[
        {items},
    ],
'''
