"""
Test 18: Utils Package (utils/)

Tests join_paths, normalize_path, PackageScanner.
"""

import pytest

from aquilia.utils import join_paths, normalize_path, PackageScanner


# ============================================================================
# join_paths
# ============================================================================

class TestJoinPaths:

    def test_simple(self):
        assert join_paths("/api", "users") == "/api/users"

    def test_strips_double_slashes(self):
        result = join_paths("/api/", "/users")
        assert "//" not in result
        assert result == "/api/users"

    def test_trailing_slash_preserved(self):
        result = join_paths("/api", "users/")
        assert result.endswith("/")

    def test_root(self):
        result = join_paths("/")
        assert result == "/"

    def test_empty_parts(self):
        result = join_paths("/api", "", "users")
        assert result == "/api/users"

    def test_multiple_parts(self):
        result = join_paths("/api", "v1", "users", "list")
        assert result == "/api/v1/users/list"

    def test_all_slashed(self):
        result = join_paths("/api/", "/v1/", "/users/")
        assert "//" not in result


# ============================================================================
# normalize_path
# ============================================================================

class TestNormalizePath:

    def test_normal(self):
        assert normalize_path("/users") == "/users"

    def test_double_slashes(self):
        assert normalize_path("/api//users") == "/api/users"

    def test_empty(self):
        assert normalize_path("") == "/"

    def test_triple_slashes(self):
        assert normalize_path("///") == "/"

    def test_mixed(self):
        assert normalize_path("/api///v1//users") == "/api/v1/users"


# ============================================================================
# PackageScanner
# ============================================================================

class TestPackageScanner:

    def test_create(self):
        scanner = PackageScanner()
        assert scanner is not None

    def test_has_scan_methods(self):
        scanner = PackageScanner()
        assert hasattr(scanner, "scan") or hasattr(scanner, "scan_package")
