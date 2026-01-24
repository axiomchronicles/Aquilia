"""
Graph analysis and cycle detection for DI system.
"""

from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict, deque

from .core import Provider, ProviderMeta
from .errors import DependencyCycleError


class DependencyGraph:
    """
    Build and analyze dependency graph.
    
    Uses Tarjan's algorithm for cycle detection.
    """
    
    def __init__(self):
        self.adj_list: Dict[str, List[str]] = defaultdict(list)  # token -> [dependencies]
        self.providers: Dict[str, Provider] = {}  # token -> provider
        self._index_counter = 0
        self._stack: List[str] = []
        self._lowlinks: Dict[str, int] = {}
        self._index: Dict[str, int] = {}
        self._on_stack: Set[str] = set()
        self._sccs: List[List[str]] = []  # Strongly connected components
    
    def add_provider(self, provider: Provider, dependencies: List[str]) -> None:
        """
        Add provider to graph.
        
        Args:
            provider: Provider instance
            dependencies: List of dependency tokens
        """
        token = provider.meta.token
        self.providers[token] = provider
        self.adj_list[token] = dependencies
    
    def detect_cycles(self) -> List[List[str]]:
        """
        Detect cycles using Tarjan's algorithm.
        
        Returns:
            List of strongly connected components (cycles)
        """
        self._index_counter = 0
        self._stack = []
        self._lowlinks = {}
        self._index = {}
        self._on_stack = set()
        self._sccs = []
        
        for token in self.providers:
            if token not in self._index:
                self._strongconnect(token)
        
        # Filter out trivial SCCs (single node with no self-loop)
        cycles = [
            scc for scc in self._sccs
            if len(scc) > 1 or (len(scc) == 1 and scc[0] in self.adj_list[scc[0]])
        ]
        
        return cycles
    
    def _strongconnect(self, token: str) -> None:
        """Tarjan's algorithm recursive helper."""
        self._index[token] = self._index_counter
        self._lowlinks[token] = self._index_counter
        self._index_counter += 1
        self._stack.append(token)
        self._on_stack.add(token)
        
        # Consider successors
        for dep in self.adj_list.get(token, []):
            if dep not in self.providers:
                # Dependency not registered (will be caught by validation)
                continue
            
            if dep not in self._index:
                # Successor not yet visited
                self._strongconnect(dep)
                self._lowlinks[token] = min(self._lowlinks[token], self._lowlinks[dep])
            elif dep in self._on_stack:
                # Successor is on stack (part of current SCC)
                self._lowlinks[token] = min(self._lowlinks[token], self._index[dep])
        
        # If token is a root, pop the stack and create SCC
        if self._lowlinks[token] == self._index[token]:
            scc = []
            while True:
                w = self._stack.pop()
                self._on_stack.remove(w)
                scc.append(w)
                if w == token:
                    break
            self._sccs.append(scc)
    
    def get_resolution_order(self) -> List[str]:
        """
        Get topological sort of providers (resolution order).
        
        Returns:
            List of tokens in dependency order
            
        Raises:
            DependencyCycleError: If cycle detected
        """
        # Kahn's algorithm for topological sort
        in_degree = defaultdict(int)
        
        for token in self.providers:
            for dep in self.adj_list[token]:
                if dep in self.providers:
                    in_degree[dep] += 1
        
        # Start with nodes that have no dependencies
        queue = deque([t for t in self.providers if in_degree[t] == 0])
        result = []
        
        while queue:
            token = queue.popleft()
            result.append(token)
            
            for dep in self.adj_list.get(token, []):
                if dep not in self.providers:
                    continue
                in_degree[dep] -= 1
                if in_degree[dep] == 0:
                    queue.append(dep)
        
        if len(result) != len(self.providers):
            # Cycle detected
            cycles = self.detect_cycles()
            if cycles:
                self._raise_cycle_error(cycles[0])
        
        return result
    
    def _raise_cycle_error(self, cycle: List[str]) -> None:
        """Raise DependencyCycleError with diagnostics."""
        # Collect location information
        locations = {}
        for token in cycle:
            provider = self.providers.get(token)
            if provider and provider.meta.line:
                locations[token] = (provider.meta.module, provider.meta.line)
        
        raise DependencyCycleError(cycle=cycle, locations=locations)
    
    def export_dot(self) -> str:
        """
        Export graph as Graphviz DOT format.
        
        Returns:
            DOT string
        """
        lines = ["digraph DependencyGraph {"]
        lines.append("  rankdir=LR;")
        lines.append("  node [shape=box];")
        
        # Add nodes
        for token, provider in self.providers.items():
            label = provider.meta.name
            scope = provider.meta.scope
            color = self._scope_color(scope)
            lines.append(f'  "{token}" [label="{label}\\n({scope})" fillcolor="{color}" style=filled];')
        
        # Add edges
        for token, deps in self.adj_list.items():
            for dep in deps:
                if dep in self.providers:
                    lines.append(f'  "{token}" -> "{dep}";')
        
        lines.append("}")
        return "\n".join(lines)
    
    def _scope_color(self, scope: str) -> str:
        """Get color for scope visualization."""
        colors = {
            "singleton": "lightblue",
            "app": "lightblue",
            "request": "lightgreen",
            "transient": "lightyellow",
            "pooled": "lightcoral",
            "ephemeral": "lightgray",
        }
        return colors.get(scope, "white")
    
    def get_tree_view(self, root: Optional[str] = None) -> str:
        """
        Get tree view of dependencies.
        
        Args:
            root: Optional root token (if None, show all roots)
            
        Returns:
            Tree view as string
        """
        if root:
            return self._tree_view_recursive(root, "", set())
        
        # Find roots (no incoming edges)
        all_deps = set()
        for deps in self.adj_list.values():
            all_deps.update(deps)
        
        roots = [t for t in self.providers if t not in all_deps]
        
        lines = []
        for root_token in roots:
            lines.append(self._tree_view_recursive(root_token, "", set()))
        
        return "\n".join(lines)
    
    def _tree_view_recursive(
        self,
        token: str,
        prefix: str,
        visited: Set[str],
    ) -> str:
        """Recursive helper for tree view."""
        if token in visited:
            return f"{prefix}├── {token} (circular)"
        
        provider = self.providers.get(token)
        if not provider:
            return f"{prefix}├── {token} (missing)"
        
        visited.add(token)
        
        lines = [f"{prefix}├── {provider.meta.name} ({provider.meta.scope})"]
        
        deps = self.adj_list.get(token, [])
        for i, dep in enumerate(deps):
            is_last = i == len(deps) - 1
            new_prefix = prefix + ("    " if is_last else "│   ")
            lines.append(self._tree_view_recursive(dep, new_prefix, visited.copy()))
        
        return "\n".join(lines)
