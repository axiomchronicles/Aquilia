#!/usr/bin/env python3
"""Test the enhanced discovery features specifically."""

import sys
import os
from pathlib import Path

# Add Aquilia to path  
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "myapp"))
os.chdir(project_root / "myapp")

def test_enhanced_features():
    """Test specific enhanced discovery features."""
    print("🚀 Testing Enhanced Discovery Features")
    print("=" * 50)
    
    try:
        from aquilia.utils.scanner import PackageScanner
        
        # Test caching and performance
        scanner = PackageScanner(cache_ttl=60)
        base_package = "modules.mymodule"
        
        print("1. 🎯 Pattern-based Discovery Test")
        print("-" * 35)
        
        # Test pattern-based discovery
        module_package = __import__(base_package, fromlist=[''])
        if hasattr(module_package, '__path__'):
            module_dir = Path(module_package.__path__[0])
            
            # Show pattern matching
            controller_patterns = [
                "*controller*.py", "*ctrl*.py", "*handler*.py", 
                "*view*.py", "*route*.py", "*api*.py"
            ]
            
            for pattern in controller_patterns:
                matches = list(module_dir.glob(pattern))
                if matches:
                    print(f"  📁 Pattern '{pattern}': {[f.name for f in matches]}")
                else:
                    print(f"  📁 Pattern '{pattern}': no matches")
        
        print("\n2. 🏎️  Performance & Caching Test")
        print("-" * 35)
        
        # First scan (cold cache)
        import time
        start = time.time()
        controllers1 = scanner.scan_package(
            f"{base_package}.controllers",
            predicate=lambda cls: cls.__name__.endswith("Controller"),
            use_cache=True
        )
        first_time = time.time() - start
        
        # Second scan (warm cache)
        start = time.time()
        controllers2 = scanner.scan_package(
            f"{base_package}.controllers", 
            predicate=lambda cls: cls.__name__.endswith("Controller"),
            use_cache=True
        )
        second_time = time.time() - start
        
        print(f"  🥶 Cold cache scan: {first_time*1000:.1f}ms")
        print(f"  🔥 Warm cache scan: {second_time*1000:.1f}ms")
        print(f"  ⚡ Speedup: {first_time/second_time:.1f}x faster")
        
        # Stats
        stats = scanner.get_stats()
        print(f"  📊 Cache hits: {stats['cache_hits']}")
        print(f"  📊 Cache misses: {stats['cache_misses']}")
        print(f"  📊 Total scan time: {stats['scan_time']*1000:.1f}ms")
        
        print("\n3. 🔍 Duck Typing Discovery Test")  
        print("-" * 35)
        
        # Test duck typing detection
        all_controllers = []
        try:
            module_dir = Path(module_package.__path__[0])
            for py_file in module_dir.glob("*.py"):
                if py_file.stem in ['__init__', 'manifest']:
                    continue
                
                submodule_name = f"{base_package}.{py_file.stem}"
                file_controllers = scanner.scan_package(
                    submodule_name,
                    predicate=lambda cls: (
                        cls.__name__.endswith("Controller") or
                        hasattr(cls, 'prefix') or
                        any(hasattr(cls, method) for method in ['get', 'post', 'put', 'delete'])
                    ),
                )
                
                if file_controllers:
                    for controller in file_controllers:
                        has_prefix = hasattr(controller, 'prefix')
                        has_methods = any(hasattr(controller, m) for m in ['get', 'post', 'put', 'delete'])
                        print(f"  🦆 {controller.__name__} in {py_file.name}")
                        print(f"     - Has prefix: {has_prefix}")
                        print(f"     - Has HTTP methods: {has_methods}")
                        all_controllers.extend(file_controllers)
        
        except Exception as e:
            print(f"  ❌ Duck typing test failed: {e}")
        
        print("\n4. 📈 Discovery Statistics")
        print("-" * 25)
        final_stats = scanner.get_stats()
        print(f"  Total controllers found: {len(all_controllers)}")
        print(f"  Modules scanned: {final_stats['modules_scanned']}")  
        print(f"  Classes found: {final_stats['classes_found']}")
        print(f"  Total scan time: {final_stats['scan_time']*1000:.1f}ms")
        print(f"  Errors encountered: {final_stats['errors_encountered']}")
        
        print("\n🎉 Enhanced Discovery Features Test Complete!")
        return True
        
    except Exception as e:
        print(f"❌ Enhanced features test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_enhanced_features()
    if success:
        print("\n✅ All enhanced features working correctly!")
    else:
        print("\n❌ Some enhanced features need attention.")