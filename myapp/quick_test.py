#!/usr/bin/env python3
"""
Quick route tester - Simple single command testing
"""
import subprocess
import sys

routes = [
    ("GET", "/test/hello"),
    ("GET", "/test/info"),
    ("GET", "/test/echo/TestMessage"),
    ("GET", "/test/health"),
    ("GET", "/mymod/"),
    ("GET", "/mymod/1"),
]

print("Testing Aquilia Routes...")
print("=" * 50)

for method, path in routes:
    url = f"http://localhost:8000{path}"
    print(f"\n{method} {path}")
    try:
        result = subprocess.run(
            ["curl", "-s", url],
            capture_output=True,
            text=True,
            timeout=3
        )
        print(result.stdout[:200])
    except Exception as e:
        print(f"Error: {e}")

print("\n" + "=" * 50)
print("Note: Server must be restarted to load new routes!")
print("Run: Ctrl+C to stop server, then 'aq run' to restart")
