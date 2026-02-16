"""
Advanced module discovery analytics and reporting.
Provides deep insights into module relationships, health metrics, and optimization suggestions.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from aquilia.cli.generators.workspace import WorkspaceGenerator


class DiscoveryAnalytics:
    """Analyze discovered modules and provide insights."""
    
    def __init__(self, workspace_name: str, workspace_path: Optional[str] = None):
        self.workspace_name = workspace_name
        self.workspace_path = Path(workspace_path or workspace_name)
        self.generator = WorkspaceGenerator(workspace_name, self.workspace_path)
        self.cache_dir = self.workspace_path / '.aquilia' / 'discovery'
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def analyze(self) -> Dict:
        """Run full discovery analysis."""
        discovered = self.generator._discover_modules()
        validation = self.generator._validate_modules(discovered)
        sorted_names = self.generator._resolve_dependencies(discovered)
        
        analysis = {
            'timestamp': datetime.now().isoformat(),
            'workspace': self.workspace_name,
            'summary': self._generate_summary(discovered),
            'modules': self._analyze_modules(discovered),
            'dependencies': self._analyze_dependencies(discovered, sorted_names),
            'metrics': self._calculate_metrics(discovered, validation),
            'recommendations': self._generate_recommendations(discovered, validation),
        }
        
        # Cache the analysis
        self._cache_analysis(analysis)
        
        return analysis
    
    def _generate_summary(self, discovered: Dict) -> Dict:
        """Generate summary statistics."""
        return {
            'total_modules': len(discovered),
            'with_services': sum(1 for m in discovered.values() if m['has_services']),
            'with_controllers': sum(1 for m in discovered.values() if m['has_controllers']),
            'with_middleware': sum(1 for m in discovered.values() if m['has_middleware']),
            'with_dependencies': sum(1 for m in discovered.values() if m.get('depends_on')),
            'with_tags': sum(1 for m in discovered.values() if m.get('tags')),
        }
    
    def _analyze_modules(self, discovered: Dict) -> Dict:
        """Analyze each module's characteristics."""
        modules_analysis = {}
        
        for name, mod in discovered.items():
            modules_analysis[name] = {
                'version': mod['version'],
                'maturity': self._assess_maturity(mod['version']),
                'components': self._get_components(mod),
                'complexity': self._calculate_complexity(mod),
                'dependency_count': len(mod.get('depends_on', [])),
                'has_author': bool(mod.get('author')),
                'tags_count': len(mod.get('tags', [])),
            }
        
        return modules_analysis
    
    def _analyze_dependencies(self, discovered: Dict, sorted_names: List[str]) -> Dict:
        """Analyze module dependency graph."""
        graph = {}
        max_depth = 0
        cyclic_detected = False
        
        def calc_depth(name: str, visited: set) -> int:
            nonlocal max_depth, cyclic_detected
            if name in visited:
                cyclic_detected = True
                return 0
            if name not in discovered:
                return 0
            
            visited.add(name)
            deps = discovered[name].get('depends_on', [])
            if not deps:
                return 1
            
            depth = 1 + max(calc_depth(dep, visited.copy()) for dep in deps)
            max_depth = max(max_depth, depth)
            return depth
        
        for name in discovered:
            graph[name] = {
                'depends_on': discovered[name].get('depends_on', []),
                'depth': calc_depth(name, set()),
            }
        
        return {
            'dependency_graph': graph,
            'max_depth': max_depth,
            'cyclic_dependencies': cyclic_detected,
            'load_order': sorted_names,
        }
    
    def _calculate_metrics(self, discovered: Dict, validation: Dict) -> Dict:
        """Calculate health and quality metrics."""
        total = len(discovered)
        
        return {
            'health_score': self._calculate_health_score(discovered, validation),
            'validation_errors': len(validation['errors']),
            'validation_warnings': len(validation['warnings']),
            'module_cohesion': total > 1 and sum(1 for m in discovered.values() if m.get('depends_on')) / total or 0,
        }
    
    def _calculate_health_score(self, discovered: Dict, validation: Dict) -> float:
        """Calculate overall health score (0-100)."""
        score = 100.0
        
        # Deduct for validation issues
        score -= len(validation['errors']) * 10
        score -= len(validation['warnings']) * 5
        
        # Bonus for good practices
        modules_with_metadata = sum(
            1 for m in discovered.values() 
            if m.get('author') and m.get('tags') and m['version'] != '0.1.0'
        )
        score += (modules_with_metadata / max(len(discovered), 1)) * 20
        
        # Bonus for well-documented dependencies
        modules_with_deps = sum(1 for m in discovered.values() if m.get('depends_on'))
        if modules_with_deps > 0:
            score += 10
        
        return max(0, min(100, score))
    
    def _generate_recommendations(self, discovered: Dict, validation: Dict) -> List[str]:
        """Generate optimization recommendations."""
        recommendations = []
        
        # Check for modules without metadata
        for name, mod in discovered.items():
            if not mod.get('author'):
                recommendations.append(
                    f"Module '{name}': Add author field to manifest"
                )
            if not mod.get('tags'):
                recommendations.append(
                    f"Module '{name}': Add tags for better discoverability"
                )
            if mod['version'] == '0.1.0':
                recommendations.append(
                    f"Module '{name}': Consider versioning (current: 0.1.0)"
                )
        
        # Check for dependency issues
        if validation['errors']:
            recommendations.append(
                f"Resolve {len(validation['errors'])} dependency errors"
            )
        
        # Suggest modularity improvements
        if len(discovered) == 1:
            recommendations.append(
                "Consider breaking down functionality into multiple modules"
            )
        
        # Check for route conflicts
        route_count = len(set(m['route_prefix'] for m in discovered.values()))
        if route_count < len(discovered):
            recommendations.append(
                "Resolve route prefix conflicts (duplicate routes detected)"
            )
        
        return recommendations
    
    def _assess_maturity(self, version: str) -> str:
        """Assess module maturity based on version."""
        try:
            major, minor, patch = map(int, version.split('.')[:3])
            if major > 1:
                return "production"
            elif major == 1 or minor >= 5:
                return "stable"
            elif minor >= 1:
                return "beta"
            else:
                return "alpha"
        except:
            return "unknown"
    
    def _get_components(self, mod: Dict) -> List[str]:
        """Get list of components in module."""
        components = []
        if mod['has_services']:
            components.append('services')
        if mod['has_controllers']:
            components.append('controllers')
        if mod['has_middleware']:
            components.append('middleware')
        return components or ['core']
    
    def _calculate_complexity(self, mod: Dict) -> str:
        """Calculate module complexity."""
        component_count = sum([
            mod['has_services'],
            mod['has_controllers'],
            mod['has_middleware'],
        ])
        dep_count = len(mod.get('depends_on', []))
        
        complexity = component_count + dep_count
        if complexity <= 1:
            return "simple"
        elif complexity <= 3:
            return "moderate"
        else:
            return "complex"
    
    def _cache_analysis(self, analysis: Dict) -> None:
        """Cache analysis results."""
        cache_file = self.cache_dir / 'analysis.json'
        with open(cache_file, 'w') as f:
            json.dump(analysis, f, indent=2, default=str)
    
    def get_cached_analysis(self, max_age_seconds: int = 3600) -> Optional[Dict]:
        """Get cached analysis if fresh."""
        cache_file = self.cache_dir / 'analysis.json'
        if not cache_file.exists():
            return None
        
        file_age = (datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)).total_seconds()
        if file_age > max_age_seconds:
            return None
        
        try:
            with open(cache_file) as f:
                return json.load(f)
        except:
            return None


def print_analysis_report(analysis: Dict) -> None:
    """Pretty print analysis report."""
    from ..utils.colors import (
        banner, section, kv, rule, step, bullet, dim, info, warning, success,
        _CHECK, _CROSS,
    )
    import click

    banner("Module Discovery Analytics")
    click.echo()

    summary = analysis['summary']
    section("Summary")
    kv("Total Modules", str(summary['total_modules']))
    kv("With Services", str(summary['with_services']))
    kv("With Controllers", str(summary['with_controllers']))
    kv("With Middleware", str(summary['with_middleware']))
    kv("With Dependencies", str(summary['with_dependencies']))
    click.echo()

    metrics = analysis['metrics']
    section("Health Metrics")
    kv("Health Score", f"{metrics['health_score']:.1f}/100")
    kv("Validation Errors", str(metrics['validation_errors']))
    kv("Validation Warnings", str(metrics['validation_warnings']))
    click.echo()

    if analysis['dependencies']['max_depth'] > 0:
        section("Dependencies")
        kv("Max Depth", str(analysis['dependencies']['max_depth']))
        cyclic = analysis['dependencies']['cyclic_detected']
        kv("Cyclic Dependencies", "Detected" if cyclic else "None")
        click.echo()

    if analysis['recommendations']:
        section("Recommendations")
        for i, rec in enumerate(analysis['recommendations'], 1):
            step(i, rec)
        click.echo()

    rule()
