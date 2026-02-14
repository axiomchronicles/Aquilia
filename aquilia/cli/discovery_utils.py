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
        # MUST NOT be a service, mixin, or test
        if cls.__name__.endswith(("Service", "Provider", "Repository", "DAO", "Manager", "Mixin")):
            return False
            
        if cls.__name__.startswith(("Test", "Mock", "Fake")):
            return False
            
        # Ignore Abstract Base Classes
        import inspect
        if inspect.isabstract(cls):
            return False
            
        # Ignore Base classes (convention)
        if cls.__name__.startswith("Base") and cls.__name__.endswith("Controller"):
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
            # Ignore Tests/Mocks/Mixins
            if cls.__name__.startswith(("Test", "Mock", "Fake", "Base")):
                return False
            if cls.__name__.endswith("Mixin"):
                return False
                
            import inspect
            if inspect.isabstract(cls):
                return False
        
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

    def _extract_metadata_from_file_static(self, file_path: Path, module_path: str) -> List[Dict[str, Any]]:
        """
        Statically extract class metadata using AST without importing.
        Finds controllers, services, and their decorators.
        """
        import ast
        results = []
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    cls_name = node.name
                    path = f"{module_path}:{cls_name}"
                    
                    item = {
                        "path": path,
                        "name": cls_name,
                        "type": None,
                        "metadata": {}
                    }
                    
                    # 1. Base classification by naming convention
                    if cls_name.endswith("Controller"):
                        item["type"] = "controller"
                    elif cls_name.endswith(("Service", "Provider", "Repository", "DAO", "Manager")):
                        item["type"] = "service"
                    
                    # 2. Check base classes
                    for base in node.bases:
                        base_name = ""
                        if isinstance(base, ast.Name):
                            base_name = base.id
                        elif isinstance(base, ast.Attribute):
                            base_name = base.attr
                            
                        if base_name == "Controller":
                            item["type"] = "controller"
                        elif base_name == "SocketController":
                            item["type"] = "socket"
                        elif base_name == "Service":
                            item["type"] = "service"

                    # 3. Check decorators for definitive classification and metadata
                    for decorator in node.decorator_list:
                        dec_name = ""
                        if isinstance(decorator, ast.Name):
                            dec_name = decorator.id
                        elif isinstance(decorator, ast.Call):
                            if isinstance(decorator.func, ast.Name):
                                dec_name = decorator.func.id
                            elif isinstance(decorator.func, ast.Attribute):
                                dec_name = decorator.func.attr
                        
                        if dec_name == "service":
                            item["type"] = "service"
                            # Extract metadata from @service(...) args
                            if isinstance(decorator, ast.Call):
                                for kw in decorator.keywords:
                                    if kw.arg in ("scope", "tag", "aliases", "factory"):
                                        if isinstance(kw.value, ast.Constant):
                                            item["metadata"][kw.arg] = kw.value.value
                                        elif isinstance(kw.value, ast.List):
                                            item["metadata"][kw.arg] = [
                                                e.value for e in kw.value.elts 
                                                if isinstance(e, ast.Constant)
                                            ]
                        elif dec_name == "Socket":
                            item["type"] = "socket"
                            # Extract namespace path from @Socket("/path")
                            if isinstance(decorator, ast.Call) and decorator.args:
                                arg = decorator.args[0]
                                if isinstance(arg, ast.Constant):
                                    item["metadata"]["namespace"] = arg.value
                        elif dec_name in ("GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"):
                            item["type"] = "controller"
                    
                    if item["type"]:
                        results.append(item)
            return results
        except Exception:
            return []

    def _is_valid_candidate_file(self, file_path: Path) -> bool:
        """
        Check if file contains potential candidates. 
        Now a wrapper around the static extractor.
        """
        return len(self._extract_metadata_from_file_static(file_path, "tmp")) > 0
    
    def discover_module_controllers_and_services(
        self,
        base_package: str,
        module_name: str,
    ) -> Tuple[List[Any], List[Any], List[Any]]:
        """
        Discover controllers, services, and socket controllers using static analysis first,
        falling back to runtime scanning only for specific standard paths.

        Returns:
            Tuple of (controllers, services, socket_controllers)
        """
        controllers_data = []
        services_data = []
        socket_controllers_data = []
        seen_paths = set()

        try:
            # Import the base module to get its path
            module_package = importlib.import_module(base_package)
            if not hasattr(module_package, '__path__'):
                return [], []
            module_dir = Path(module_package.__path__[0])
        except (ImportError, AttributeError, ValueError):
            return [], []

        # Scan files recursively using static analysis
        try:
            for py_file in module_dir.rglob("*.py"):
                if py_file.stem in ['__init__', 'manifest', 'config', 'settings', 'faults', 'middleware']:
                    continue
                
                # Calculate submodule path
                rel_path = py_file.relative_to(module_dir)
                parts = [base_package] + list(rel_path.parent.parts) + [rel_path.stem]
                submodule_path = ".".join([p for p in parts if p and p != "."])
                
                # Static extraction
                items = self._extract_metadata_from_file_static(py_file, submodule_path)
                for item in items:
                    if item["path"] in seen_paths:
                        continue
                    seen_paths.add(item["path"])
                    
                    if item["type"] == "controller":
                        controllers_data.append(item)
                    elif item["type"] == "service":
                        services_data.append(item)
                    elif item["type"] == "socket":
                        socket_controllers_data.append(item)
                        
        except Exception as e:
            if self.verbose:
                print(f"    ⚠️  Static discovery error: {e}")

        # Fallback to runtime scanning for standard packages if nothing found (backward compat)
        if not seen_paths:
            # ... (Runtime strategies remain as fallback)
            pass

        return controllers_data, services_data, socket_controllers_data
    
    def clean_manifest_lists(
        self,
        manifest_content: str,
        discovered_controllers: List[Dict[str, Any]],
        discovered_services: List[Dict[str, Any]],
        module_dir: Optional[Path] = None,
        discovered_sockets: Optional[List[Dict[str, Any]]] = None,
    ) -> Tuple[str, int, int]:
        """
        Clean and update manifest.py with properly classified items.
        Bidirectional sync: 
        1. Class metadata -> Manifest (Upgrade to ServiceConfig)
        2. Manifest -> FS (Dead link detection)
        
        Socket controllers are separated from regular controllers and
        written to the ``socket_controllers`` field of AppManifest.
        """
        import ast
        
        # Extract current declarations using AST
        current_services_raw = self._extract_list_from_manifest_ast(manifest_content, "services")
        current_controllers_raw = self._extract_list_from_manifest_ast(manifest_content, "controllers")
        current_sockets_raw = self._extract_list_from_manifest_ast(manifest_content, "socket_controllers")
        
        # Build a set of known socket paths from discovery for fast lookup
        _discovered_sockets = discovered_sockets or []
        known_socket_paths = {s["path"] for s in _discovered_sockets if isinstance(s, dict) and "path" in s}
        
        # Separate misplaced sockets out of the controllers list.
        # A controller item is a socket if:
        #   a) it was discovered as type="socket", OR
        #   b) its class name ends with "Socket" (heuristic fallback)
        cleaned_controllers_raw = []
        migrated_sockets = []
        for item in current_controllers_raw:
            p = get_class_path(item)
            class_name = p.rsplit(":", 1)[-1] if ":" in p else ""
            if p in known_socket_paths or class_name.endswith("Socket"):
                migrated_sockets.append(item)
                if self.verbose:
                    print(f"    ↪ Migrating socket controller from controllers → socket_controllers: {p}")
            else:
                cleaned_controllers_raw.append(item)
        
        current_controllers_raw = cleaned_controllers_raw
        # Merge migrated sockets into the existing socket_controllers list (dedup)
        existing_socket_paths = {get_class_path(s) for s in current_sockets_raw}
        for sock in migrated_sockets:
            if get_class_path(sock) not in existing_socket_paths:
                current_sockets_raw.append(sock)
                existing_socket_paths.add(get_class_path(sock))
        
        # Helper to get class_path
        def get_class_path(item: Union[str, Dict[str, Any]]) -> str:
            if isinstance(item, str):
                return item
            return item.get("class_path", "")

        # 1. Dead Link Resolution & Redundancy Cleanup
        if module_dir:
            valid_services_raw = []
            service_registry = set()
            
            # First pass: Identify all classes already registered via ServiceConfig
            for item in current_services_raw:
                if isinstance(item, dict): # ServiceConfig
                    service_registry.add(item.get("class_path", ""))
                    service_registry.update(item.get("aliases", []))

            # Second pass: Filter dead links AND redundant strings
            for item in current_services_raw:
                p = get_class_path(item)
                
                # Check for dead link
                if not self._verify_path_exists(p, module_dir):
                    if self.verbose:
                        print(f"    ⚠️  Removing dead link: {p}")
                    continue
                
                # Check for redundancy: If item is a string but already covered by a ServiceConfig
                if isinstance(item, str) and item in service_registry:
                    # We might have multiple strings, or a string that's an alias. 
                    # If it's a string that matches a class_path of a ServiceConfig, it's redundant.
                    # If it's a string that is an ALIAS of a ServiceConfig, it's also redundant.
                    # We keep the ServiceConfig.
                    
                    # Ensure we don't remove if this IS the only registration (impossible here because we checked service_registry)
                    # But we need to be careful not to remove ALL if only strings exist.
                    # Since we only added to service_registry from DICTs (ServiceConfig), this is safe.
                    if self.verbose:
                        print(f"    ⚠️  Removing redundant registration: {p} (already registered via ServiceConfig or alias)")
                    continue

                valid_services_raw.append(item)
            current_services_raw = valid_services_raw

            valid_controllers_raw = []
            for item in current_controllers_raw:
                p = get_class_path(item)
                if self._verify_path_exists(p, module_dir):
                    valid_controllers_raw.append(item)
                elif self.verbose:
                    print(f"    ⚠️  Removing dead link: {p}")
            current_controllers_raw = valid_controllers_raw

        # 2. Merger & Metadata Upgrade
        existing_service_paths = set()
        for s in current_services_raw:
            existing_service_paths.add(get_class_path(s))
            if isinstance(s, dict) and "aliases" in s:
                existing_service_paths.update(s["aliases"])
                
        existing_controller_paths = {get_class_path(c) for c in current_controllers_raw}
        
        services_added = 0
        controllers_added = 0
        
        final_services_raw = list(current_services_raw)
        final_controllers_raw = list(current_controllers_raw)

        # Add discovered services (with metadata aware config generation)
        for disc in discovered_services:
            path = disc["path"]
            if path in existing_service_paths:
                # Potential upgrade of existing string to ServiceConfig if metadata found?
                # For now, we only add NEW items with metadata.
                continue
            
            # If metadata found, create a rich entry
            if disc["metadata"]:
                meta = disc["metadata"]
                # Formulate ServiceConfig source
                args = [f'class_path="{path}"']
                if "scope" in meta: args.append(f'scope="{meta["scope"]}"')
                if "aliases" in meta: args.append(f'aliases={meta["aliases"]}')
                if "tag" in meta: args.append(f'tag="{meta["tag"]}"')
                
                source = f"ServiceConfig({', '.join(args)})"
                final_services_raw.append({"type": "complex", "source": source, "class_path": path})
            else:
                final_services_raw.append(path)
            
            services_added += 1

        # Add discovered controllers (excluding sockets)
        for disc in discovered_controllers:
            path = disc["path"]
            if path not in existing_controller_paths:
                final_controllers_raw.append(path)
                controllers_added += 1

        # Add discovered socket controllers
        final_sockets_raw = list(current_sockets_raw)
        sockets_added = 0
        for disc in _discovered_sockets:
            path = disc["path"]
            if path not in existing_socket_paths:
                final_sockets_raw.append(path)
                existing_socket_paths.add(path)
                sockets_added += 1
        
        # Update manifest content
        updated_content = manifest_content
        
        # We always regenerate if dead links were removed or items added
        old_block_match = self._find_block_match(manifest_content, "Services with detailed DI configuration")
        if old_block_match:
            indent = old_block_match.group(1)
            new_block = self._generate_services_block_ast(final_services_raw, indent=indent)
            if new_block != old_block_match.group(0):
                updated_content = updated_content.replace(old_block_match.group(0), new_block)
        
        old_block_match = self._find_block_match(manifest_content, "Controllers with routing")
        if old_block_match:
            indent = old_block_match.group(1)
            new_block = self._generate_controllers_block_ast(final_controllers_raw, indent=indent)
            if new_block != old_block_match.group(0):
                updated_content = updated_content.replace(old_block_match.group(0), new_block)
        
        # Handle socket_controllers: If sockets were migrated or discovered,
        # ensure a socket_controllers=[] field exists in the manifest.
        if final_sockets_raw:
            updated_content = self._ensure_socket_controllers_field(
                updated_content, final_sockets_raw
            )
        
        return updated_content, services_added, controllers_added

    def _ensure_socket_controllers_field(
        self, content: str, sockets: List[Union[str, Dict[str, Any]]]
    ) -> str:
        """
        Ensure the manifest has a ``socket_controllers=[...]`` field
        with the given socket controller paths.

        If the field already exists, replace its contents.
        If not, insert it right after the ``controllers=[...]`` block.
        """
        import ast
        import re

        # Format socket items
        formatted = []
        for item in sockets:
            if isinstance(item, str):
                formatted.append(f'"{item}"')
            elif isinstance(item, dict) and "source" in item:
                formatted.append(item["source"])
            elif isinstance(item, dict) and "path" in item:
                formatted.append(f'"{item["path"]}"')

        if not formatted:
            return content

        # Check if socket_controllers= already exists in the file
        existing_match = re.search(
            r'(\s*)socket_controllers\s*=\s*\[(.*?)\]',
            content,
            re.DOTALL,
        )

        if existing_match:
            # Replace existing socket_controllers block
            indent = existing_match.group(1)
            inner_indent = indent + "    "
            items_str = (",\n" + inner_indent).join(formatted)
            replacement = f"{indent}socket_controllers=[\n{inner_indent}{items_str},\n{indent}]"
            content = content[:existing_match.start()] + replacement + content[existing_match.end():]
        else:
            # Insert after the controllers=[] block
            ctrl_match = re.search(
                r'([ \t]*)controllers\s*=\s*\[.*?\],',
                content,
                re.DOTALL,
            )
            if ctrl_match:
                indent = ctrl_match.group(1)
                inner_indent = indent + "    "
                items_str = (",\n" + inner_indent).join(formatted)
                socket_block = f"\n{indent}socket_controllers=[\n{inner_indent}{items_str},\n{indent}],"
                insert_pos = ctrl_match.end()
                content = content[:insert_pos] + socket_block + content[insert_pos:]

        return content

    def _verify_path_exists(self, item_path: str, module_dir: Path) -> bool:
        """Verify that an import path exists relative to module_dir."""
        if not item_path:
            return False

        # Exempt standard libraries and types
        if "." in item_path:
            prefix = item_path.split('.')[0]
            if prefix in ("typing", "builtins", "datetime", "json", "aquilia"):
                return True

        if ':' not in item_path:
            return False
        
        try:
            mod_path, class_name = item_path.split(':', 1)
            parts = mod_path.split('.')
            if len(parts) < 2: return False
            
            # Reconstruct file path
            target = module_dir
            for part in parts[2:]:
                target = target / part
            
            py_file = target.with_suffix('.py')
            if py_file.exists():
                # Static check for class existence
                content = py_file.read_text(encoding='utf-8', errors='ignore')
                import ast
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef) and node.name == class_name:
                        return True
                return False
            
            # Check if it might be an __init__.py export
            init_file = target / "__init__.py"
            if init_file.exists():
                return class_name in init_file.read_text()

            return False
        except:
            return False

    def _find_block_match(self, content: str, comment_text: str):
        """
        Find a block match using a regex that pattern matches leading whitespace.
        Uses a more robust pattern to avoid premature matching of nested brackets.
        """
        # Look for the comment, then the list start, then anything until a '],' 
        # that is at the end of a line and followed by the next section.
        pattern = rf'([ \t]*)#\s*{re.escape(comment_text)}\s*\n[ \t]*[a-z_]+=\s*\[(.*?)\n\1\],\s*\n'
        return re.search(pattern, content, re.DOTALL)

    def _extract_list_from_manifest_ast(self, content: str, key: str) -> List[Union[str, str]]:
        """
        Extract list items from manifest.py using AST to preserve complex objects.
        Returns a list where items are either strings (paths) or the original code for complex objects.
        """
        import ast
        try:
            tree = ast.parse(content)
            
            # Find the manifest = AppManifest(...) call
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign) and len(node.targets) == 1:
                    target = node.targets[0]
                    if isinstance(target, ast.Name) and target.id == "manifest":
                        if isinstance(node.value, ast.Call):
                            # We found the AppManifest call, now look for the keyword argument
                            for keyword in node.value.keywords:
                                if keyword.arg == key and isinstance(keyword.value, ast.List):
                                    items = []
                                    for elt in keyword.value.elts:
                                        # Get original source for this element
                                        start_line = elt.lineno
                                        end_line = getattr(elt, "end_lineno", start_line)
                                        start_col = elt.col_offset
                                        end_col = getattr(elt, "end_col_offset", -1)
                                        
                                        lines = content.splitlines()
                                        if start_line == end_line:
                                            item_source = lines[start_line-1][start_col:end_col]
                                        else:
                                            # Multi-line item
                                            item_lines = lines[start_line-1:end_line]
                                            item_lines[0] = item_lines[0][start_col:]
                                            item_lines[-1] = item_lines[-1][:end_col]
                                            item_source = "\n".join(item_lines)
                                        
                                        # Clean up trailing commas or whitespace if necessary, 
                                        # but usually ast.get_source or similar is better.
                                        # Since we don't have a reliable get_source in standard ast, 
                                        # we use this slice.
                                        
                                        # If it's a string, we want the value for deduplication logic, 
                                        # but we'll store the source for preservation.
                                        # To help clean_manifest_lists, let's return a richer object if it's complex.
                                        
                                        if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                            items.append(elt.value)
                                        elif isinstance(elt, ast.Call):
                                            # Try to extract class_path and aliases from ServiceConfig call
                                            class_path = ""
                                            aliases = []
                                            for kw in elt.keywords:
                                                if kw.arg == "class_path" and isinstance(kw.value, ast.Constant):
                                                    class_path = kw.value.value
                                                elif kw.arg == "aliases":
                                                    if isinstance(kw.value, ast.List):
                                                        aliases = [e.value for e in kw.value.elts if isinstance(e, ast.Constant)]
                                                    elif isinstance(kw.value, ast.Constant):
                                                        aliases = [kw.value.value]
                                            
                                            # If not found in keywords, maybe it's positional
                                            if not class_path and elt.args and isinstance(elt.args[0], ast.Constant):
                                                class_path = elt.args[0].value

                                            items.append({
                                                "type": "complex",
                                                "source": item_source.strip().rstrip(','),
                                                "class_path": class_path,
                                                "aliases": aliases
                                            })
                                        else:
                                            items.append({
                                                "type": "complex",
                                                "source": item_source.strip().rstrip(',')
                                            })
                                    return items
            return []
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
        pattern = r'([ \t]*)#\s*Services with detailed DI configuration\s*\n\s*services=\s*\[(.*?)\],\s*\n'
        match = re.search(pattern, content, re.DOTALL)
        if match:
            return match.group(0)
        return ""
    
    @staticmethod
    def _extract_controllers_block(content: str) -> str:
        """Extract the controllers=[ ... ] block from manifest."""
        pattern = r'([ \t]*)#\s*Controllers with routing\s*\n\s*controllers=\s*\[(.*?)\],\s*\n'
        match = re.search(pattern, content, re.DOTALL)
        if match:
            return match.group(0)
        return ""
    
    @staticmethod
    def _generate_services_block_ast(services: List[Union[str, Dict[str, Any]]], indent: str = "    ") -> str:
        """Generate the services=[ ... ] block for manifest."""
        if not services:
            return f'{indent}# Services with detailed DI configuration\n{indent}services=[],\n'
        
        formatted_items = []
        for item in services:
            if isinstance(item, str):
                formatted_items.append(f'"{item}"')
            elif isinstance(item, dict) and "source" in item:
                formatted_items.append(item["source"])
        
        items = (",\n" + indent + "    ").join(formatted_items)
        return f'''{indent}# Services with detailed DI configuration
{indent}services=[
{indent}    {items},
{indent}],
'''
    
    @staticmethod
    def _generate_controllers_block_ast(controllers: List[Union[str, Dict[str, Any]]], indent: str = "    ") -> str:
        """Generate the controllers=[ ... ] block for manifest."""
        if not controllers:
            return f'{indent}# Controllers with routing\n{indent}controllers=[],\n'
        
        formatted_items = []
        for item in controllers:
            if isinstance(item, str):
                formatted_items.append(f'"{item}"')
            elif isinstance(item, dict) and "source" in item:
                formatted_items.append(item["source"])
                
        items = (",\n" + indent + "    ").join(formatted_items)
        return f'''{indent}# Controllers with routing
{indent}controllers=[
{indent}    {items},
{indent}],
'''

