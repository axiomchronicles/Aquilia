"""
Dependency graph analysis with Tarjan's algorithm for cycle detection.
"""

from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class GraphNode:
    """Dependency graph node."""
    
    name: str
    dependencies: List[str] = field(default_factory=list)
    
    # Tarjan's algorithm state
    index: Optional[int] = None
    lowlink: Optional[int] = None
    on_stack: bool = False
    
    def __hash__(self) -> int:
        return hash(self.name)
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, GraphNode):
            return NotImplemented
        return self.name == other.name


class DependencyGraph:
    """
    Dependency graph with cycle detection and topological sorting.
    
    Uses Tarjan's strongly connected components algorithm for O(V+E) cycle detection.
    """
    
    def __init__(self):
        self._nodes: Dict[str, GraphNode] = {}
        self._adjacency: Dict[str, List[str]] = {}
    
    def add_node(self, name: str, dependencies: List[str]) -> None:
        """
        Add node to graph.
        
        Args:
            name: Node name
            dependencies: List of dependency names
        """
        node = GraphNode(name=name, dependencies=dependencies)
        self._nodes[name] = node
        self._adjacency[name] = dependencies
        
        # Ensure all dependencies exist as nodes
        for dep in dependencies:
            if dep not in self._nodes:
                self._nodes[dep] = GraphNode(name=dep)
                self._adjacency[dep] = []
    
    def topological_sort(self) -> List[str]:
        """
        Compute topological sort of graph (dependency order).
        
        Returns:
            List of node names in dependency order (dependencies first)
            
        Raises:
            DependencyCycleError: If cycle detected
        """
        # Check for cycles first
        cycle = self.find_cycle()
        if cycle:
            from .errors import DependencyCycleError
            raise DependencyCycleError(cycle=cycle)
        
        # Kahn's algorithm for topological sort
        in_degree: Dict[str, int] = {name: 0 for name in self._nodes}
        
        for name, deps in self._adjacency.items():
            for dep in deps:
                in_degree[dep] += 1
        
        # Start with nodes that have no dependencies
        queue = [name for name, degree in in_degree.items() if degree == 0]
        result: List[str] = []
        
        while queue:
            node_name = queue.pop(0)
            result.append(node_name)
            
            # Process dependencies
            for dep_name in self._adjacency.get(node_name, []):
                in_degree[dep_name] -= 1
                if in_degree[dep_name] == 0:
                    queue.append(dep_name)
        
        # Reverse to get dependency-first order
        return list(reversed(result))
    
    def find_cycle(self) -> Optional[List[str]]:
        """
        Find cycle in graph using Tarjan's algorithm.
        
        Returns:
            List of node names forming cycle, or None if no cycle
        """
        # Tarjan's algorithm state
        index_counter = [0]
        stack: List[str] = []
        lowlinks: Dict[str, int] = {}
        index: Dict[str, int] = {}
        on_stack: Set[str] = set()
        cycles: List[List[str]] = []
        
        def strongconnect(node_name: str) -> None:
            """Tarjan's strongconnect subroutine."""
            index[node_name] = index_counter[0]
            lowlinks[node_name] = index_counter[0]
            index_counter[0] += 1
            stack.append(node_name)
            on_stack.add(node_name)
            
            # Process dependencies
            for dep_name in self._adjacency.get(node_name, []):
                if dep_name not in index:
                    strongconnect(dep_name)
                    lowlinks[node_name] = min(
                        lowlinks[node_name],
                        lowlinks[dep_name],
                    )
                elif dep_name in on_stack:
                    lowlinks[node_name] = min(
                        lowlinks[node_name],
                        index[dep_name],
                    )
            
            # If node is root of SCC, pop the cycle
            if lowlinks[node_name] == index[node_name]:
                component: List[str] = []
                while True:
                    w = stack.pop()
                    on_stack.remove(w)
                    component.append(w)
                    if w == node_name:
                        break
                
                # If component has more than 1 node, it's a cycle
                if len(component) > 1:
                    cycles.append(component)
        
        # Run Tarjan's algorithm
        for node_name in self._nodes:
            if node_name not in index:
                strongconnect(node_name)
        
        # Return first cycle found
        if cycles:
            return cycles[0]
        
        return None
    
    def get_dependencies(self, node_name: str) -> List[str]:
        """
        Get direct dependencies of node.
        
        Args:
            node_name: Node name
            
        Returns:
            List of dependency names
        """
        return self._adjacency.get(node_name, [])
    
    def get_transitive_dependencies(self, node_name: str) -> Set[str]:
        """
        Get transitive closure of dependencies.
        
        Args:
            node_name: Node name
            
        Returns:
            Set of all transitive dependency names
        """
        visited: Set[str] = set()
        
        def visit(name: str) -> None:
            if name in visited:
                return
            visited.add(name)
            for dep in self._adjacency.get(name, []):
                visit(dep)
        
        visit(node_name)
        visited.discard(node_name)  # Remove self
        return visited
    
    def get_dependents(self, node_name: str) -> List[str]:
        """
        Get nodes that depend on given node (reverse dependencies).
        
        Args:
            node_name: Node name
            
        Returns:
            List of dependent node names
        """
        dependents: List[str] = []
        for name, deps in self._adjacency.items():
            if node_name in deps:
                dependents.append(name)
        return dependents
    
    def to_dict(self) -> Dict[str, List[str]]:
        """
        Export graph as adjacency dict.
        
        Returns:
            Dict mapping node names to dependency lists
        """
        return self._adjacency.copy()
    
    def to_dot(self) -> str:
        """
        Export graph as DOT format for visualization.
        
        Returns:
            DOT graph string
        """
        lines = ["digraph dependencies {"]
        lines.append("  rankdir=LR;")
        lines.append("  node [shape=box, style=rounded];")
        
        # Add nodes
        for name in self._nodes:
            lines.append(f'  "{name}";')
        
        # Add edges
        for name, deps in self._adjacency.items():
            for dep in deps:
                lines.append(f'  "{name}" -> "{dep}";')
        
        lines.append("}")
        return "\n".join(lines)
    
    def get_load_order(self) -> List[str]:
        """
        Get load order (topological sort).
        
        Alias for topological_sort().
        
        Returns:
            List of node names in load order
        """
        return self.topological_sort()
    
    def validate(self) -> Tuple[bool, Optional[List[str]]]:
        """
        Validate graph for cycles.
        
        Returns:
            Tuple of (is_valid, cycle_if_invalid)
        """
        cycle = self.find_cycle()
        return (cycle is None, cycle)
    
    def get_roots(self) -> List[str]:
        """
        Get root nodes (no dependencies).
        
        Returns:
            List of root node names
        """
        roots: List[str] = []
        for name, deps in self._adjacency.items():
            if not deps:
                roots.append(name)
        return roots
    
    def get_leaves(self) -> List[str]:
        """
        Get leaf nodes (no dependents).
        
        Returns:
            List of leaf node names
        """
        has_dependents: Set[str] = set()
        for deps in self._adjacency.values():
            has_dependents.update(deps)
        
        leaves: List[str] = []
        for name in self._nodes:
            if name not in has_dependents:
                leaves.append(name)
        
        return leaves
    
    def get_layers(self) -> List[List[str]]:
        """
        Get dependency layers (parallel execution groups).
        
        Returns:
            List of layers, each layer contains nodes that can be loaded in parallel
        """
        layers: List[List[str]] = []
        remaining = set(self._nodes.keys())
        loaded: Set[str] = set()
        
        while remaining:
            # Find nodes whose dependencies are all loaded
            layer: List[str] = []
            for name in remaining:
                deps = set(self._adjacency.get(name, []))
                if deps.issubset(loaded):
                    layer.append(name)
            
            if not layer:
                # Cycle detected
                break
            
            layers.append(layer)
            remaining -= set(layer)
            loaded.update(layer)
        
        return layers
    
    def __len__(self) -> int:
        """Get number of nodes in graph."""
        return len(self._nodes)
    
    def __contains__(self, name: str) -> bool:
        """Check if node exists in graph."""
        return name in self._nodes
    
    def __repr__(self) -> str:
        return f"DependencyGraph({len(self._nodes)} nodes)"
