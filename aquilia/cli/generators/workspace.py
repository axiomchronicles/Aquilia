"""Workspace generator."""

from pathlib import Path
from typing import Optional
import textwrap


class WorkspaceGenerator:
    """Generate Aquilia workspace structure."""
    
    def __init__(
        self,
        name: str,
        path: Path,
        minimal: bool = False,
        template: Optional[str] = None,
    ):
        self.name = name
        self.path = path
        self.minimal = minimal
        self.template = template
    
    def generate(self) -> None:
        """Generate workspace structure."""
        self.path.mkdir(parents=True, exist_ok=True)
        
        # Create directory structure
        self._create_directories()
        
        # Create manifest files
        self._create_workspace_manifest()
        self._create_config_files()
        
        # Create additional files
        if not self.minimal:
            self._create_gitignore()
            self._create_readme()
    
    def _create_directories(self) -> None:
        """Create workspace directories."""
        dirs = ['modules', 'config']
        
        if not self.minimal:
            dirs.extend(['artifacts', 'runtime'])
        
        for dir_name in dirs:
            (self.path / dir_name).mkdir(exist_ok=True)
    
    def _extract_field(self, content: str, pattern: str, default: str) -> str:
        """Extract a single field from manifest content."""
        import re
        match = re.search(pattern, content)
        return match.group(1) if match else default
    
    def _extract_list(self, content: str, pattern: str, default: list = None) -> list:
        """Extract a list field from manifest content."""
        import re
        if default is None:
            default = []
        match = re.search(pattern, content, re.DOTALL)
        if not match:
            return default
        
        list_content = match.group(1)
        # Extract quoted strings from the list
        items = re.findall(r'"([^"]+)"', list_content)
        return items if items else default
    
    def generate_workspace_module_config(self, discovered_modules: dict) -> str:
        """
        Generate enhanced workspace module configuration from discovered manifests and runtime discovery.
        
        Args:
            discovered_modules: Dictionary of discovered module data with enhanced discovery results
            
        Returns:
            String containing workspace module configuration with all discovered controllers/services
        """
        lines = []
        
        for mod_name, mod_data in discovered_modules.items():
            # Generate module configuration
            version = mod_data.get('version', '0.1.0')
            description = mod_data.get('description', f'{mod_name.capitalize()} module')
            route_prefix = mod_data.get('route_prefix', f'/{mod_name}')
            tags = mod_data.get('tags', [])
            
            # Build enhanced module config with discovered resources
            base_config = f'Module("{mod_name}", version="{version}", description="{description}")'
            
            # Add route prefix (8 spaces = .module indent + 1 tab)
            config_chain = f'{base_config}\n        .route_prefix("{route_prefix}")'
            
            # Add tags
            if tags:
                tags_str = ', '.join(f'"{tag}"' for tag in tags)
                config_chain += f'\n        .tags({tags_str})'
            
            # Add discovered controllers registration
            controllers_list = mod_data.get('controllers_list', [])
            if controllers_list and len(controllers_list) > 0:
                controllers_str = ',\n            '.join(f'"{ctrl}"' for ctrl in controllers_list)
                config_chain += f'\n        .register_controllers(\n            {controllers_str}\n        )'
            
            # Add discovered services registration  
            services_list = mod_data.get('services_list', [])
            if services_list and len(services_list) > 0:
                services_str = ',\n            '.join(f'"{svc}"' for svc in services_list)
                config_chain += f'\n        .register_services(\n            {services_str}\n        )'
            
            # .module at same level as .integrate (4 spaces)
            module_line = f'    .module({config_chain})'
            lines.append(module_line)
        
        return '\n'.join(lines)
    
    def update_workspace_config(self, workspace_path: Path, discovered_modules: dict) -> None:
        """
        Update workspace.py with auto-discovered module configurations.
        
        Args:
            workspace_path: Path to workspace.py file
            discovered_modules: Dictionary of discovered module data
        """
        if not workspace_path.exists():
            return
        
        content = workspace_path.read_text()
        
        # Generate new module configuration
        new_config = self.generate_workspace_module_config(discovered_modules)
        
        import re
        
        # Strategy: Find the right place to insert modules
        # 1. Look for existing modules and remove them
        # 2. Find the comment "# Integrations" and insert before it
        
        # Remove existing module blocks by looking for pattern: 
        # Lines with .module(Module(...)) that might span multiple lines
        lines = content.split('\n')
        new_lines = []
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Check if this line starts a .module(...) block
            # Handles both single-line and multi-line formats
            if '.module(' in line:
                # Skip lines until we find the closing ) of this module block
                paren_depth = 0
                start_i = i
                while i < len(lines):
                    paren_depth += lines[i].count('(') - lines[i].count(')')
                    if paren_depth <= 0 and i > start_i:
                        i += 1
                        break
                    i += 1
            else:
                new_lines.append(line)
                i += 1
        
        content = '\n'.join(new_lines)
        
        # Now find where to insert modules
        # Look for "# Integrations - Configure core systems"
        integrations_comment = "    # Integrations - Configure core systems"
        
        if integrations_comment in content:
            # Insert before this comment
            content = content.replace(
                integrations_comment,
                new_config + '\n\n' + integrations_comment
            )
        else:
            # Fallback: find .integrate( and insert before it
            integrate_match = re.search(r'(\s*\.integrate\()', content)
            if integrate_match:
                insertion_point = integrate_match.start()
                # Get the indentation
                indent = len(integrate_match.group(1)) - len(integrate_match.group(1).lstrip())
                content = content[:insertion_point] + new_config + '\n\n    ' + content[insertion_point:]
        
        # Clean up extra newlines
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        
        # Write back
        workspace_path.write_text(content)
        print(f"✅ Updated workspace.py with {len(discovered_modules)} module configurations")

    def _discover_modules(self) -> dict:
        """Enhanced module discovery with intelligent classification."""
        from aquilia.cli.discovery_utils import EnhancedDiscovery
        
        modules_dir = self.path / 'modules'
        discovered_modules = {}
        
        if not modules_dir.exists():
            return discovered_modules
        
        discovery = EnhancedDiscovery(verbose=False)
        
        # Find all module directories with manifest.py
        module_dirs = [d for d in modules_dir.iterdir() 
                      if d.is_dir() and (d / 'manifest.py').exists()]
        
        # Parse all manifests
        for mod_dir in module_dirs:
            mod_name = mod_dir.name
            try:
                manifest_content = (mod_dir / 'manifest.py').read_text()
                
                # Extract all module metadata
                version = self._extract_field(manifest_content, r'version="([^"]+)"', "0.1.0")
                description = self._extract_field(manifest_content, r'description="([^"]+)"', mod_name.capitalize())
                route_prefix = self._extract_field(manifest_content, r'route_prefix="([^"]+)"', f"/{mod_name}")
                author = self._extract_field(manifest_content, r'author="([^"]+)"', "")
                tags = self._extract_list(manifest_content, r'tags=\[(.*?)\]', [])
                base_path = self._extract_field(manifest_content, r'base_path="([^"]+)"', f"modules.{mod_name}")
                depends_on = self._extract_list(manifest_content, r'depends_on=\[(.*?)\]', [])
                
                # Extract current manifest declarations (baseline)
                manifest_services_list = self._extract_list(manifest_content, r'services=\s*\[(.*?)\]', [])
                manifest_controllers_list = self._extract_list(manifest_content, r'controllers=\s*\[(.*?)\]', [])
                manifest_middleware_list = self._extract_list(manifest_content, r'middleware=\s*\[(.*?)\]', [])
                
                # ENHANCED: Use intelligent discovery to properly classify items
                try:
                    discovered_controllers, discovered_services = discovery.discover_module_controllers_and_services(
                        base_path, mod_name
                    )
                    
                    # Use discovered classification (more accurate than manifest)
                    services_list = discovered_services if discovered_services else manifest_services_list
                    controllers_list = discovered_controllers if discovered_controllers else manifest_controllers_list
                    
                except Exception:
                    # Fallback to manifest declarations if discovery fails
                    services_list = manifest_services_list
                    controllers_list = manifest_controllers_list
                
                # Check for actual declarations/discoveries
                has_services = len(services_list) > 0
                has_controllers = len(controllers_list) > 0
                has_middleware = len(manifest_middleware_list) > 0
                
                discovered_modules[mod_name] = {
                    'name': mod_name,
                    'path': mod_dir,
                    'version': version,
                    'description': description,
                    'route_prefix': route_prefix,
                    'author': author,
                    'tags': tags,
                    'base_path': base_path,
                    'depends_on': depends_on,
                    'has_services': has_services,
                    'has_controllers': has_controllers,
                    'has_middleware': has_middleware,
                    'services_list': services_list,
                    'controllers_list': controllers_list,
                    'middleware_list': manifest_middleware_list,
                    'services_count': len(services_list),
                    'controllers_count': len(controllers_list),
                    'middleware_count': len(manifest_middleware_list),
                    'manifest_path': mod_dir / 'manifest.py',
                }
            except Exception:
                # Silently skip modules with parsing errors
                pass
        
        return discovered_modules
    
    def _resolve_dependencies(self, modules: dict) -> list:
        """Topologically sort modules based on dependencies (Kahn's algorithm)."""
        if not modules:
            return []
        
        # Build dependency graph
        graph = {name: mod.get('depends_on', []) for name, mod in modules.items()}
        in_degree = {name: 0 for name in modules}
        
        # Calculate in-degrees
        for name in modules:
            for dep in graph.get(name, []):
                if dep in in_degree:
                    in_degree[name] += 1
        
        # Process nodes with no dependencies
        sorted_modules = []
        queue = [name for name, degree in in_degree.items() if degree == 0]
        
        while queue:
            node = queue.pop(0)
            sorted_modules.append(node)
            
            # Reduce in-degree for dependent modules
            for name in modules:
                if node in graph.get(name, []):
                    in_degree[name] -= 1
                    if in_degree[name] == 0:
                        queue.append(name)
        
        # Return sorted modules, fall back to alphabetical if cycles detected
        return sorted_modules if len(sorted_modules) == len(modules) else sorted(modules.keys())
    
    def _validate_modules(self, modules: dict) -> dict:
        """Validate modules and detect conflicts."""
        validation = {
            'valid': True,
            'warnings': [],
            'errors': [],
        }
        
        route_prefixes = {}
        for name, mod in modules.items():
            route = mod['route_prefix']
            if route in route_prefixes:
                validation['warnings'].append(
                    f"Route prefix conflict: '{route}' used by both '{name}' and '{route_prefixes[route]}'"
                )
            else:
                route_prefixes[route] = name
            
            # Check for missing dependencies
            for dep in mod.get('depends_on', []):
                if dep not in modules:
                    validation['errors'].append(
                        f"Module '{name}' depends on '{dep}' which is not installed"
                    )
                    validation['valid'] = False
        
        return validation
    
    def _create_workspace_manifest(self) -> None:
        """Create aquilia.py configuration (Python-based, production-grade)."""
        # Discover all modules with enhanced detection
        discovered = self._discover_modules()
        module_registrations = ""
        
        if discovered:
            # Validate modules
            validation = self._validate_modules(discovered)
            
            # Resolve dependencies and get sorted order
            sorted_names = self._resolve_dependencies(discovered)
            
            module_lines = []
            for mod_name in sorted_names:
                mod = discovered[mod_name]
                
                # Build enhanced module registration with proper formatting
                # Format: .module(Module("name", version="...", description="...").route_prefix(...).tags(...).register_controllers(...).register_services(...))
                
                base_config = f'Module("{mod["name"]}", version="{mod["version"]}", description="{mod["description"]}")'
                
                # Add route prefix
                config_chain = f'{base_config}\n        .route_prefix("{mod["route_prefix"]}")'
                
                # Add tags
                if mod.get('tags'):
                    tags_part = ", ".join(f'"{t}"' for t in mod['tags'])
                    config_chain += f'\n        .tags({tags_part})'
                
                # Add discovered controllers registration
                controllers_list = mod.get('controllers_list', [])
                if controllers_list and len(controllers_list) > 0:
                    controllers_str = ',\n            '.join(f'"{ctrl}"' for ctrl in controllers_list)
                    config_chain += f'\n        .register_controllers(\n            {controllers_str}\n        )'
                
                # Add discovered services registration  
                services_list = mod.get('services_list', [])
                if services_list and len(services_list) > 0:
                    services_str = ',\n            '.join(f'"{svc}"' for svc in services_list)
                    config_chain += f'\n        .register_services(\n            {services_str}\n        )'
                
                # .module(Module(...) on same line, then chain methods indented
                module_line = f'.module({config_chain}\n    ))'
                module_lines.append(module_line)
            
            if module_lines:
                # Indent each module block with 4 spaces
                module_registrations = "\n" + "\n".join("    " + line.replace("\n", "\n    ") for line in module_lines)
        
        content = textwrap.dedent(f'''\
            """
            Aquilia Workspace Configuration - Production Grade
            Generated by: aq init workspace {self.name}

            This file defines the WORKSPACE STRUCTURE (modules, integrations).
            It is:
            - Environment-agnostic
            - Version-controlled and shared across team
            - Type-safe with full IDE support
            - Observable via introspection

            Runtime settings (host, port, workers) come from config/dev.yaml or config/prod.yaml.

            Separation of concerns:
            - aquilia.py (THIS FILE) = Workspace structure (modules, integrations)
            - config/base.yaml = Shared configuration defaults
            - config/{{mode}}.yaml = Environment-specific runtime settings (dev, prod)
            - Environment variables = Override mechanism for secrets and env-specific values
            """

            from aquilia import Workspace, Module, Integration
            from datetime import timedelta
            from aquilia.sessions import SessionPolicy, PersistencePolicy, ConcurrencyPolicy, TransportPolicy


            # Define workspace structure
            workspace = (
                Workspace(
                    name="{self.name}",
                    version="0.1.0",
                    description="Aquilia workspace",
                ){"" if not module_registrations else chr(10) + "    # Auto-detected modules" + module_registrations}
                # Add modules here with explicit configuration:
                # .module(Module("auth", version="1.0.0", description="Authentication module").route_prefix("/api/v1/auth").depends_on("core"))
                # .module(Module("users", version="1.0.0", description="User management").route_prefix("/api/v1/users").depends_on("auth", "core"))

                # Integrations - Configure core systems
                .integrate(Integration.di(auto_wire=True, manifest_validation=True))
                .integrate(Integration.registry(
                    mode="auto",  # "dev", "prod", "auto" (env-based)
                    fingerprint_verification=True,
                ))
                .integrate(Integration.routing(
                    strict_matching=True,
                    version_support=True,
                    compression=True,
                ))
                .integrate(Integration.fault_handling(
                    default_strategy="propagate",
                    metrics_enabled=True,
                ))
                .integrate(Integration.patterns())

                # Sessions - Configure session management
                .sessions(
                    policies=[
                        # Default session policy for web users
                        SessionPolicy(
                            name="default",
                            ttl=timedelta(days=7),
                            idle_timeout=timedelta(hours=1),
                            rotate_on_privilege_change=True,
                            persistence=PersistencePolicy(
                                enabled=True,
                                store_name="memory",
                                write_through=True,
                            ),
                            concurrency=ConcurrencyPolicy(
                                max_sessions_per_principal=5,
                                behavior_on_limit="evict_oldest",
                            ),
                            transport=TransportPolicy(
                                adapter="cookie",
                                cookie_httponly=True,
                                cookie_secure=False,  # Set to True in production
                                cookie_samesite="lax",
                            ),
                            scope="user",
                        ),
                    ],
                )

                # Security - Enable/disable security features
                .security(
                    cors_enabled=False,
                    csrf_protection=False,
                    helmet_enabled=True,
                    rate_limiting=True,
                )

                # Telemetry - Enable observability
                .telemetry(
                    tracing_enabled=False,
                    metrics_enabled=True,
                    logging_enabled=True,
                )
            )


            # Export for CLI/server
            __all__ = ["workspace"]
        ''').strip()

        (self.path / 'workspace.py').write_text(content)
    
    def _create_config_files(self) -> None:
        """Create environment configuration files."""
        # base.yaml - Shared defaults
        base_config = textwrap.dedent("""
            # Base Server Configuration - Shared Across All Environments
            # Environment-specific files (dev.yaml, prod.yaml) override these values
            
            server:
              mode: dev
              host: 127.0.0.1
              port: 8000
              reload: false
              workers: 1
              backlog: 2048
              timeout_keep_alive: 5
              timeout_notify: 30
              access_log: true
        """).strip()
        
        (self.path / 'config' / 'base.yaml').write_text(base_config)
        
        # dev.yaml - Development environment
        dev_config = textwrap.dedent("""
            # Development Environment - Server Configuration
            # Overrides base.yaml for development
            
            server:
              mode: dev
              host: 127.0.0.1
              port: 8000
              reload: true                # Hot-reload on file changes
              workers: 1                  # Single worker for debugging
              backlog: 2048
              timeout_keep_alive: 10
              timeout_notify: 30
              access_log: true
        """).strip()
        
        (self.path / 'config' / 'dev.yaml').write_text(dev_config)
        
        # prod.yaml - Production environment
        prod_config = textwrap.dedent("""
            # Production Environment - Server Configuration
            # Overrides base.yaml for production
            
            server:
              mode: prod
              host: 0.0.0.0               # Bind to all interfaces (behind reverse proxy)
              port: 8000
              reload: false               # No hot-reload in production
              workers: 4                  # Multi-worker for concurrency
              backlog: 2048
              timeout_keep_alive: 5
              timeout_notify: 60          # Graceful shutdown timeout
              access_log: false           # Disable in production (use reverse proxy logging)
        """).strip()
        
        (self.path / 'config' / 'prod.yaml').write_text(prod_config)
    
    def _create_gitignore(self) -> None:
        """Create .gitignore file."""
        content = textwrap.dedent("""
            # Python
            __pycache__/
            *.py[cod]
            *$py.class
            *.so
            .Python
            env/
            venv/
            ENV/
            
            # Aquilia
            artifacts/
            runtime/
            *.crous
            
            # IDE
            .vscode/
            .idea/
            *.swp
            *.swo
            
            # OS
            .DS_Store
            Thumbs.db
        """).strip()
        
        (self.path / '.gitignore').write_text(content)
    
    def _create_readme(self) -> None:
        """Create README.md file."""
        content = textwrap.dedent(f"""
            # {self.name}
            
            Aquilia workspace generated with `aq init workspace {self.name}`.
            
            ## Structure
            
            ```
            {self.name}/
              aquilia.py          # Workspace configuration (Python)
              modules/            # Application modules
              config/             # Environment-specific configs
                base.yaml        # Base config
                dev.yaml         # Development config
                prod.yaml        # Production config
              artifacts/          # Compiled artifacts
              runtime/            # Runtime state
            ```
            
            ## Configuration Architecture
            
            Aquilia uses a **professional separation of concerns**:
            
            - **`aquilia.py`** - Workspace structure (modules, integrations)
              - Version-controlled and shared across team
              - Environment-agnostic
              - Type-safe Python API
            
            - **`config/*.yaml`** - Runtime settings (host, port, workers)
              - Environment-specific (dev, prod, staging)
              - Can contain secrets (not committed)
              - Merged in order: base → environment → env vars
            
            ## Getting Started
            
            ### Add a module
            
            ```bash
            aq add module users
            ```
            
            This will update `aquilia.py`:
            
            ```python
            workspace = (
                Workspace("{self.name}", version="0.1.0")
                .module(Module("users").route_prefix("/users"))
                ...
            )
            ```
            
            ### Run development server
            
            ```bash
            aq run
            ```
            
            This loads: `aquilia.py` + `config/base.yaml` + `config/dev.yaml`
            
            ### Run production server
            
            ```bash
            aq run --mode=prod
            ```
            
            This loads: `aquilia.py` + `config/base.yaml` + `config/prod.yaml`
            
            ## Session Management
            
            Enable sessions with unique Aquilia syntax in `aquilia.py`:
            
            ```python
            workspace = (
                Workspace("{self.name}", version="0.1.0")
                .integrate(Integration.sessions(
                    policy=SessionPolicy(ttl=timedelta(days=7)),
                    store=MemoryStore(max_sessions=1000),
                ))
            )
            ```
            
            Then use in controllers:
            
            ```python
            from aquilia import session, authenticated, stateful
            
            @GET("/profile")
            @authenticated
            async def profile(ctx, user: SessionPrincipal):
                return {{"user_id": user.id}}
            
            @POST("/cart")
            @stateful
            async def cart(ctx, state: SessionState):
                state._data['items'].append(item)
            ```
            
            ## Commands
            
            - `aq add module <name>` - Add new module
            - `aq validate` - Validate configuration
            - `aq compile` - Compile to artifacts
            - `aq run` - Development server
            - `aq run --mode=prod` - Production server
            - `aq serve` - Production server (frozen artifacts)
            - `aq freeze` - Generate immutable artifacts
            - `aq inspect routes` - Inspect compiled routes
            - `aq sessions list` - List active sessions
            - `aq doctor` - Diagnose issues
            
            ## Documentation
            
            See Aquilia documentation for complete guides.
        """).strip()
        
        (self.path / 'README.md').write_text(content)
