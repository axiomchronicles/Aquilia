"""
Template Manager - Compilation, linting, and manifest integration.

Provides:
- Template compilation to crous artifacts
- Template linting and validation
- Manifest-driven template discovery
- DI integration
"""

from typing import Any, Dict, List, Optional, Set
from pathlib import Path
from dataclasses import dataclass, field
import hashlib
import json
import pickle
from datetime import datetime
from jinja2 import Environment, TemplateSyntaxError, meta
from jinja2.exceptions import TemplateNotFound, UndefinedError

from .engine import TemplateEngine
from .loader import TemplateLoader
from .bytecode_cache import BytecodeCache, CrousBytecodeCache


@dataclass
class TemplateLintIssue:
    """
    Template lint issue.
    
    Attributes:
        template_name: Template file name
        line: Line number (if available)
        column: Column number (if available)
        severity: Issue severity (error, warning, info)
        message: Human-readable message
        code: Issue code (e.g., "undefined-variable", "disallowed-filter")
    """
    
    template_name: str
    severity: str  # "error", "warning", "info"
    message: str
    code: str
    line: Optional[int] = None
    column: Optional[int] = None
    context: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "template_name": self.template_name,
            "line": self.line,
            "column": self.column,
            "severity": self.severity,
            "message": self.message,
            "code": self.code,
            "context": self.context,
        }
    
    def __str__(self) -> str:
        """Format as human-readable string."""
        location = f"{self.template_name}"
        if self.line:
            location += f":{self.line}"
            if self.column:
                location += f":{self.column}"
        
        return f"{location}: {self.severity}: {self.message} [{self.code}]"


@dataclass
class TemplateMetadata:
    """Template metadata for compilation."""
    
    name: str
    path: str
    module: Optional[str]
    hash: str
    size: int
    mtime: float
    compiled_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "name": self.name,
            "path": self.path,
            "module": self.module,
            "hash": self.hash,
            "size": self.size,
            "mtime": self.mtime,
            "compiled_at": self.compiled_at,
        }


class TemplateManager:
    """
    Template compilation and management.
    
    Provides compilation, linting, and manifest integration for templates.
    
    Args:
        engine: Template engine
        loader: Template loader
        config: Application config (optional)
    
    Example:
        manager = TemplateManager(engine, loader)
        
        # Compile all templates
        result = await manager.compile_all()
        print(f"Compiled {result['count']} templates")
        
        # Lint templates
        issues = await manager.lint_all()
        for issue in issues:
            print(issue)
    """
    
    def __init__(
        self,
        engine: TemplateEngine,
        loader: TemplateLoader,
        config: Optional[Any] = None
    ):
        self.engine = engine
        self.loader = loader
        self.config = config
    
    async def compile_all(
        self,
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Compile all templates to crous artifact.
        
        Args:
            output_path: Output file path (default: artifacts/templates.crous)
        
        Returns:
            Compilation result with fingerprint, count, and metadata
        """
        output_path = output_path or "artifacts/templates.crous"
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Discover all templates
        template_names = self.loader.list_templates()
        
        # Build metadata for each template
        templates_metadata: Dict[str, TemplateMetadata] = {}
        
        for name in template_names:
            try:
                # Get template source
                source, filename, _ = self.loader.get_source(self.engine.env, name)
                
                # Compute hash
                source_hash = self._compute_hash(source)
                
                # Get file info
                if filename:
                    file_path = Path(filename)
                    size = file_path.stat().st_size if file_path.exists() else len(source)
                    mtime = file_path.stat().st_mtime if file_path.exists() else 0
                else:
                    size = len(source)
                    mtime = 0
                
                # Extract module from name
                module = self._extract_module(name)
                
                templates_metadata[name] = TemplateMetadata(
                    name=name,
                    path=filename or name,
                    module=module,
                    hash=source_hash,
                    size=size,
                    mtime=mtime,
                    compiled_at=datetime.utcnow().isoformat()
                )
                
                # Compile template (triggers bytecode cache)
                self.engine.get_template(name)
                
            except Exception as e:
                # Template failed to compile
                print(f"Warning: Failed to compile {name}: {e}")
        
        # Compute fingerprint
        fingerprint = self._compute_fingerprint(templates_metadata)
        
        # Build crous envelope
        envelope = {
            "__format__": "crous",
            "schema_version": "1.0",
            "artifact_type": "templates",
            "fingerprint": fingerprint,
            "created_at": datetime.utcnow().isoformat(),
            "payload": {
                "templates": {
                    name: meta.to_dict()
                    for name, meta in templates_metadata.items()
                },
                "count": len(templates_metadata),
            }
        }
        
        # Write artifact atomically
        temp_file = output_file.with_suffix(".tmp")
        try:
            with open(temp_file, "wb") as f:
                pickle.dump(envelope, f)
            temp_file.replace(output_file)
        except Exception:
            if temp_file.exists():
                temp_file.unlink()
            raise
        
        # Persist bytecode cache
        if hasattr(self.engine.bytecode_cache, "save"):
            self.engine.bytecode_cache.save()
        
        return {
            "fingerprint": fingerprint,
            "count": len(templates_metadata),
            "output": str(output_file),
            "templates": list(templates_metadata.keys()),
        }
    
    async def lint_all(
        self,
        strict_undefined: bool = True
    ) -> List[TemplateLintIssue]:
        """
        Lint all templates.
        
        Checks for:
        - Syntax errors
        - Undefined variables
        - Disallowed filters/tests/globals
        
        Args:
            strict_undefined: Treat undefined variables as errors
        
        Returns:
            List of lint issues
        """
        issues: List[TemplateLintIssue] = []
        
        # Discover all templates
        template_names = self.loader.list_templates()
        
        for name in template_names:
            issues.extend(await self._lint_template(name, strict_undefined))
        
        return issues
    
    async def _lint_template(
        self,
        template_name: str,
        strict_undefined: bool = True
    ) -> List[TemplateLintIssue]:
        """Lint single template."""
        issues: List[TemplateLintIssue] = []
        
        try:
            # Get template source
            source, filename, _ = self.loader.get_source(self.engine.env, template_name)
            
            # Parse template AST
            try:
                ast = self.engine.env.parse(source)
            except TemplateSyntaxError as e:
                issues.append(TemplateLintIssue(
                    template_name=template_name,
                    line=e.lineno,
                    severity="error",
                    message=str(e),
                    code="syntax-error"
                ))
                return issues
            
            # Find undefined variables
            if strict_undefined:
                undefined = meta.find_undeclared_variables(ast)
                
                # Filter out common globals and template variables
                known_globals = set(self.engine.env.globals.keys())
                known_globals.update(["request", "session", "identity", "csrf_token", "config"])
                
                undefined = undefined - known_globals
                
                for var in undefined:
                    issues.append(TemplateLintIssue(
                        template_name=template_name,
                        severity="warning",
                        message=f"Potentially undefined variable: {var}",
                        code="undefined-variable"
                    ))
            
            # Check for disallowed filters (if sandboxed)
            if self.engine.sandbox:
                allowed_filters = self.engine._sandbox.policy.allowed_filters
                
                # Extract filter usage from AST (simplified)
                # In production, use proper AST visitor
                for line in source.split("\n"):
                    if "|" in line:
                        # Simple heuristic: extract filter names
                        parts = line.split("|")
                        for part in parts[1:]:
                            filter_name = part.strip().split()[0].split("(")[0]
                            if filter_name and filter_name not in allowed_filters:
                                issues.append(TemplateLintIssue(
                                    template_name=template_name,
                                    severity="error",
                                    message=f"Disallowed filter: {filter_name}",
                                    code="disallowed-filter"
                                ))
        
        except TemplateNotFound:
            issues.append(TemplateLintIssue(
                template_name=template_name,
                severity="error",
                message="Template not found",
                code="not-found"
            ))
        except Exception as e:
            issues.append(TemplateLintIssue(
                template_name=template_name,
                severity="error",
                message=f"Lint error: {str(e)}",
                code="lint-error"
            ))
        
        return issues
    
    async def inspect(self, template_name: str) -> Dict[str, Any]:
        """
        Inspect template metadata.
        
        Args:
            template_name: Template name
        
        Returns:
            Template inspection data
        """
        try:
            # Get source
            source, filename, _ = self.loader.get_source(self.engine.env, template_name)
            
            # Compute hash
            source_hash = self._compute_hash(source)
            
            # Check if compiled
            template = self.engine.get_template(template_name)
            is_compiled = template.module is not None
            
            # Get file info
            if filename:
                file_path = Path(filename)
                size = file_path.stat().st_size if file_path.exists() else len(source)
                mtime = file_path.stat().st_mtime if file_path.exists() else 0
            else:
                size = len(source)
                mtime = 0
            
            return {
                "name": template_name,
                "path": filename,
                "hash": source_hash,
                "size": size,
                "mtime": mtime,
                "compiled": is_compiled,
                "cached": template_name in self.engine._template_cache,
            }
        
        except TemplateNotFound:
            return {
                "name": template_name,
                "error": "Template not found"
            }
    
    def _compute_hash(self, content: str) -> str:
        """Compute SHA256 hash of content."""
        hash_digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        return f"sha256:{hash_digest}"
    
    def _compute_fingerprint(self, templates: Dict[str, TemplateMetadata]) -> str:
        """Compute fingerprint of all templates."""
        # Canonical representation: sorted list of (name, hash)
        items = sorted(
            (name, meta.hash)
            for name, meta in templates.items()
        )
        canonical = json.dumps(items, separators=(",", ":"))
        hash_digest = hashlib.sha256(canonical.encode()).hexdigest()
        return f"sha256:{hash_digest}"
    
    def _extract_module(self, template_name: str) -> Optional[str]:
        """Extract module name from template path."""
        if ":" in template_name:
            return template_name.split(":", 1)[0]
        elif "/" in template_name:
            return template_name.split("/", 1)[0]
        return None
