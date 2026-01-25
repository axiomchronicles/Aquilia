#!/usr/bin/env python3
"""Test script to verify controller discovery fix."""

import sys
import os
from pathlib import Path

# Add Aquilia to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "myapp"))  # Add myapp to path for modules import
os.chdir(project_root / "myapp")

def test_enhanced_discovery():
    """Test the enhanced controller discovery with intelligence."""
    print("Testing ENHANCED controller discovery with intelligence...")
    
    try:
        from aquilia.utils.scanner import PackageScanner
        
        # Create enhanced scanner
        scanner = PackageScanner(cache_ttl=60)  # 1 minute cache
        base_package = "modules.mymodule"
        
        print(f"🔍 Enhanced scanning {base_package} for controllers...")
        
        # Test enhanced discovery with all patterns
        enhanced_controllers = []
        discovery_cache = {}
        discovery_stats = {'scanned_locations': [], 'found_patterns': [], 'cache_hits': 0}
        
        # Strategy 1: Standard subpackage scanning with multiple patterns
        standard_locations = [
            f"{base_package}.controllers",
            f"{base_package}.test_routes", 
            f"{base_package}.handlers",
            f"{base_package}.views",
            f"{base_package}.routes",
        ]
        
        for location in standard_locations:
            try:
                controllers = scanner.scan_package(
                    location,
                    predicate=lambda cls: (
                        cls.__name__.endswith("Controller") or
                        cls.__name__.endswith("Handler") or
                        cls.__name__.endswith("View") or
                        hasattr(cls, '__controller_routes__') or
                        hasattr(cls, 'prefix')
                    ),
                )
                enhanced_controllers.extend(controllers)
                if controllers:
                    discovery_stats['scanned_locations'].append(location)
                    print(f"  📦 {location}: {len(controllers)} controllers")
            except ImportError:
                print(f"  📦 {location}: not found")
                pass
        
        # Strategy 2: Enhanced individual file scanning with pattern detection
        import importlib
        try:
            module_package = importlib.import_module(base_package)
            if hasattr(module_package, '__path__'):
                module_dir = Path(module_package.__path__[0])
                
                # Intelligent file pattern matching
                controller_patterns = [
                    "*controller*.py", "*ctrl*.py", "*handler*.py", 
                    "*view*.py", "*route*.py", "*api*.py",
                    "*endpoint*.py", "*resource*.py"
                ]
                
                print(f"  📁 Scanning module directory: {module_dir}")
                candidate_files = set()
                for pattern in controller_patterns:
                    matched = list(module_dir.glob(pattern))
                    if matched:
                        print(f"    🎯 Pattern '{pattern}': {[f.name for f in matched]}")
                        candidate_files.update(matched)
                
                # Also scan all Python files (fallback)
                all_py_files = set(module_dir.glob("*.py"))
                other_files = all_py_files - candidate_files - {
                    module_dir / "__init__.py", 
                    module_dir / "manifest.py"
                }
                
                if other_files:
                    print(f"    📄 Other files to check: {[f.name for f in sorted(other_files)]}")
                
                # Process priority files first
                for py_file in sorted(candidate_files) + sorted(other_files):
                    if py_file.stem in ['__init__', 'manifest']:
                        continue
                    
                    # Quick content analysis for performance
                    try:
                        content = py_file.read_text(encoding='utf-8', errors='ignore')
                        if not ('Controller' in content or 'Handler' in content or 
                               'View' in content or 'class ' in content):
                            continue
                    except Exception:
                        continue
                    
                    # Scan the file
                    submodule_name = f"{base_package}.{py_file.stem}"
                    try:
                        file_controllers = scanner.scan_package(
                            submodule_name,
                            predicate=lambda cls: (
                                cls.__name__.endswith("Controller") or
                                cls.__name__.endswith("Handler") or
                                cls.__name__.endswith("View") or
                                hasattr(cls, '__controller_routes__') or
                                hasattr(cls, 'prefix') or
                                # Duck typing for controller-like classes
                                any(hasattr(cls, method) for method in ['get', 'post', 'put', 'delete'])
                            ),
                        )
                        if file_controllers:
                            print(f"    ✅ {py_file.name}: {[c.__name__ for c in file_controllers]}")
                            enhanced_controllers.extend(file_controllers)
                            if py_file not in candidate_files:
                                discovery_stats['found_patterns'].append(py_file.name)
                        else:
                            print(f"    ❌ {py_file.name}: no controllers")
                            
                    except Exception as file_error:
                        print(f"    ⚠️  Error scanning {py_file.name}: {file_error}")
                        
        except Exception as module_scan_error:
            print(f"  ⚠️  Module directory scan failed: {module_scan_error}")
        
        # Deduplicate results
        unique_controllers = {}
        for controller in enhanced_controllers:
            key = f"{controller.__module__}:{controller.__name__}"
            if key not in unique_controllers:
                unique_controllers[key] = controller
        
        final_controllers = list(unique_controllers.keys())
        
        print(f"\n📊 Enhanced Discovery Results:")
        print(f"   Total controllers found: {len(final_controllers)}")
        print(f"   Scanned locations: {discovery_stats['scanned_locations']}")
        if discovery_stats['found_patterns']:
            print(f"   Unexpected patterns: {discovery_stats['found_patterns']}")
        
        for controller in sorted(final_controllers):
            print(f"   🎯 {controller}")
        
        # Test scanner stats
        stats = scanner.get_stats()
        print(f"\n📈 Scanner Performance:")
        print(f"   Cache hits: {stats['cache_hits']}")
        print(f"   Cache misses: {stats['cache_misses']}")
        print(f"   Modules scanned: {stats['modules_scanned']}")
        print(f"   Classes found: {stats['classes_found']}")
        print(f"   Scan time: {stats['scan_time']:.3f}s")
        
        return len(final_controllers)
        
    except Exception as e:
        print(f"Enhanced test failed: {e}")
        import traceback
        traceback.print_exc()
        return 0

if __name__ == "__main__":
    count = test_enhanced_discovery()
    print(f"\n🎉 Enhanced Discovery test complete - found {count} controllers total")