#!/usr/bin/env python3
"""
Test script for Aquilia myapp routes.
Usage: python test_routes.py
"""

import requests
import json
from typing import Dict, Any


BASE_URL = "http://localhost:8000"
COLORS = {
    "green": "\033[92m",
    "red": "\033[91m",
    "blue": "\033[94m",
    "yellow": "\033[93m",
    "reset": "\033[0m"
}


def colored(text: str, color: str) -> str:
    """Return colored text."""
    return f"{COLORS.get(color, '')}{text}{COLORS['reset']}"


def test_route(method: str, path: str, data: Dict[str, Any] = None, expected_status: int = 200):
    """Test a single route."""
    url = f"{BASE_URL}{path}"
    print(f"\n{colored('→', 'blue')} Testing: {colored(f'{method} {path}', 'yellow')}")
    
    try:
        if method == "GET":
            response = requests.get(url, timeout=5)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=5)
        elif method == "PUT":
            response = requests.put(url, json=data, timeout=5)
        elif method == "DELETE":
            response = requests.delete(url, timeout=5)
        else:
            print(f"{colored('✗', 'red')} Unknown method: {method}")
            return
        
        status_match = response.status_code == expected_status
        status_color = "green" if status_match else "red"
        
        print(f"  Status: {colored(str(response.status_code), status_color)}")
        
        if response.content:
            try:
                json_data = response.json()
                print(f"  Response: {json.dumps(json_data, indent=4)}")
            except:
                print(f"  Response: {response.text[:200]}")
        
        if response.headers.get("X-Custom-Test"):
            print(f"  Custom Header: {response.headers.get('X-Custom-Test')}")
        
        if status_match:
            print(f"  {colored('✓ PASSED', 'green')}")
        else:
            print(f"  {colored('✗ FAILED', 'red')} (Expected {expected_status})")
        
        return status_match
        
    except requests.exceptions.ConnectionError:
        print(f"{colored('✗ ERROR', 'red')}: Could not connect to server")
        print(f"  Make sure the server is running on {BASE_URL}")
        return False
    except Exception as e:
        print(f"{colored('✗ ERROR', 'red')}: {str(e)}")
        return False


def main():
    """Run all tests."""
    print(colored("=" * 60, "blue"))
    print(colored("  Aquilia API Test Suite", "blue"))
    print(colored("=" * 60, "blue"))
    
    tests = [
        # Test routes
        ("GET", "/test/hello", None, 200),
        ("GET", "/test/info", None, 200),
        ("GET", "/test/echo/HelloWorld", None, 200),
        ("GET", "/test/health", None, 200),
        ("GET", "/test/headers", None, 200),
        ("GET", "/test/status/200", None, 200),
        ("GET", "/test/status/404", None, 404),
        ("POST", "/test/data", {"name": "test", "value": 123}, 200),
        
        # MymodController routes
        ("GET", "/mymod/", None, 200),
        ("GET", "/mymod/1", None, 200),
        ("POST", "/mymod/", {"name": "Test Item"}, 201),
        ("PUT", "/mymod/1", {"name": "Updated Item"}, 200),
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        if test_route(*test):
            passed += 1
        else:
            failed += 1
    
    print(f"\n{colored('=' * 60, 'blue')}")
    print(f"  Results: {colored(f'{passed} passed', 'green')}, {colored(f'{failed} failed', 'red')}")
    print(colored("=" * 60, "blue"))


if __name__ == "__main__":
    main()
