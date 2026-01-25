#!/usr/bin/env python3
"""
Comprehensive Aquilia Sessions Testing Script.

This script performs regression testing of ALL session features using the requests library.
It tests:
- Basic session operations (create, read, update, delete)
- Authentication and authorization
- Session state management
- Session decorators and guards
- Error handling and fault scenarios
- Performance and bulk operations
- Session analytics and tracking

Run this script while the Aquilia development server is running.
"""

import requests
import json
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
import sys
import traceback


class SessionTester:
    """Comprehensive session testing class."""
    
    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url
        self.session = requests.Session()  # Persistent session for cookies
        self.test_results = []
        self.current_session_id = None
        self.current_user_id = None
        
    def log(self, message: str, level: str = "INFO"):
        """Log test message with timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"[{timestamp}] {level}: {message}")
    
    def test_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make test request and handle common response patterns."""
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = self.session.request(method, url, **kwargs)
            
            # Log request
            self.log(f"{method} {endpoint} -> {response.status_code}")
            
            # Try to parse JSON response
            try:
                data = response.json()
            except:
                data = {"raw_response": response.text}
            
            return {
                "success": response.status_code < 400,
                "status_code": response.status_code,
                "data": data,
                "response": response
            }
        except Exception as e:
            self.log(f"Request failed: {str(e)}", "ERROR")
            return {
                "success": False,
                "error": str(e),
                "data": {}
            }
    
    def assert_test(self, condition: bool, test_name: str, details: str = ""):
        """Assert test condition and record result."""
        if condition:
            self.log(f"✅ PASS: {test_name} {details}", "PASS")
            self.test_results.append({"test": test_name, "status": "PASS", "details": details})
            return True
        else:
            self.log(f"❌ FAIL: {test_name} {details}", "FAIL")
            self.test_results.append({"test": test_name, "status": "FAIL", "details": details})
            return False
    
    def run_all_tests(self):
        """Run all session tests."""
        self.log("🚀 Starting comprehensive Aquilia session tests")
        
        try:
            # Basic session operations
            self.test_basic_session_operations()
            
            # Authentication and authorization
            self.test_authentication_flow()
            
            # Session data operations
            self.test_session_data_operations()
            
            # Typed session state
            self.test_typed_session_state()
            
            # Advanced decorators and guards
            self.test_advanced_decorators()
            
            # Session ID operations
            self.test_session_id_operations()
            
            # Error handling
            self.test_error_handling()
            
            # Performance testing
            self.test_performance()
            
            # Analytics testing
            self.test_analytics()
            
            # Cleanup
            self.test_cleanup()
            
        except Exception as e:
            self.log(f"Test suite failed with exception: {str(e)}", "ERROR")
            traceback.print_exc()
        
        # Print summary
        self.print_test_summary()
    
    def test_basic_session_operations(self):
        """Test basic session operations."""
        self.log("🔍 Testing basic session operations")
        
        # Test session info (no session yet)
        result = self.test_request("GET", "/session-test/info")
        self.assert_test(
            result["success"] and not result["data"].get("has_session", True),
            "Session info with no session",
            "Should return has_session=false"
        )
        
        # Test session creation
        result = self.test_request("POST", "/session-test/create")
        self.assert_test(
            result["success"] and "session_id" in result["data"],
            "Session creation",
            f"Created session: {result['data'].get('session_id', 'N/A')[:20]}..."
        )
        
        if result["success"]:
            self.current_session_id = result["data"].get("session_id")
        
        # Test session info (with session)
        result = self.test_request("GET", "/session-test/info")
        self.assert_test(
            result["success"] and result["data"].get("has_session", False),
            "Session info with session",
            f"Session exists: {result['data'].get('session_id', 'N/A')[:20]}..."
        )
    
    def test_authentication_flow(self):
        """Test authentication and logout flow."""
        self.log("🔐 Testing authentication flow")
        
        # Test authentication requirement (should fail)
        result = self.test_request("GET", "/session-test/require-auth-test")
        self.assert_test(
            not result["success"] and result["status_code"] == 403,
            "Authentication requirement enforcement",
            "Should return 403 when not authenticated"
        )
        
        # Authenticate user
        auth_data = {
            "username": "test_user_regression",
            "role": "admin",
            "email": "test@regression.com",
            "email_verified": True
        }
        result = self.test_request("POST", "/session-test/authenticate", json=auth_data)
        self.assert_test(
            result["success"] and result["data"].get("is_authenticated", False),
            "User authentication",
            f"Authenticated user: {result['data'].get('user_id', 'N/A')}"
        )
        
        if result["success"]:
            self.current_user_id = result["data"].get("user_id")
        
        # Test authentication requirement (should pass now)
        result = self.test_request("GET", "/session-test/require-auth-test")
        self.assert_test(
            result["success"] and result["data"].get("authenticated", False),
            "Authentication requirement with valid auth",
            "Should pass with authenticated session"
        )
        
        # Test logout
        result = self.test_request("POST", "/session-test/logout")
        self.assert_test(
            result["success"] and "former_user_id" in result["data"],
            "User logout",
            f"Logged out user: {result['data'].get('former_user_id', 'N/A')}"
        )
    
    def test_session_data_operations(self):
        """Test session data CRUD operations."""
        self.log("💾 Testing session data operations")
        
        # Get initial session data
        result = self.test_request("GET", "/session-test/data")
        initial_keys = len(result["data"].get("data", {})) if result["success"] else 0
        self.assert_test(
            result["success"],
            "Get session data",
            f"Initial data keys: {initial_keys}"
        )
        
        # Update session data
        test_data = {
            "test_string": "regression_test_value",
            "test_number": 42,
            "test_boolean": True,
            "test_list": [1, 2, 3, "test"],
            "test_object": {
                "nested": "value",
                "timestamp": datetime.now().isoformat()
            }
        }
        result = self.test_request("PUT", "/session-test/data", json=test_data)
        self.assert_test(
            result["success"] and len(result["data"].get("updated_keys", [])) == len(test_data),
            "Update session data",
            f"Updated {len(test_data)} keys"
        )
        
        # Verify data was updated
        result = self.test_request("GET", "/session-test/data")
        if result["success"]:
            data = result["data"].get("data", {})
            self.assert_test(
                data.get("test_string") == "regression_test_value",
                "Verify string data persistence",
                f"String value: {data.get('test_string')}"
            )
            self.assert_test(
                data.get("test_number") == 42,
                "Verify number data persistence",
                f"Number value: {data.get('test_number')}"
            )
            self.assert_test(
                data.get("test_boolean") is True,
                "Verify boolean data persistence",
                f"Boolean value: {data.get('test_boolean')}"
            )
        
        # Delete specific key
        result = self.test_request("DELETE", "/session-test/data/test_string")
        self.assert_test(
            result["success"] and result["data"].get("deleted_value") == "regression_test_value",
            "Delete specific data key",
            f"Deleted key with value: {result['data'].get('deleted_value')}"
        )
    
    def test_typed_session_state(self):
        """Test typed session state management."""
        self.log("🏷️ Testing typed session state")
        
        # Get initial user state
        result = self.test_request("GET", "/session-test/state/user")
        self.assert_test(
            result["success"],
            "Get typed user state",
            f"Username: {result['data'].get('username', 'N/A')}"
        )
        
        # Update user state
        user_data = {
            "username": "regression_user",
            "email": "regression@test.com",
            "role": "tester",
            "permissions": ["read", "write", "test"],
            "preferences": {
                "theme": "dark",
                "language": "en",
                "notifications": True
            },
            "is_verified": True
        }
        result = self.test_request("PUT", "/session-test/state/user", json=user_data)
        self.assert_test(
            result["success"] and result["data"].get("login_count", 0) > 0,
            "Update typed user state",
            f"Login count: {result['data'].get('login_count', 0)}"
        )
        
        # Test cart state
        result = self.test_request("GET", "/session-test/state/cart")
        self.assert_test(
            result["success"] and result["data"].get("item_count", -1) == 0,
            "Get cart state",
            f"Cart items: {result['data'].get('item_count', 0)}"
        )
        
        # Add items to cart
        items = [
            {"name": "Test Item 1", "price": 19.99, "quantity": 2},
            {"name": "Test Item 2", "price": 29.99, "quantity": 1},
            {"name": "Test Item 3", "price": 9.99, "quantity": 3}
        ]
        
        total_expected = 0
        for item in items:
            result = self.test_request("POST", "/session-test/state/cart/add", json=item)
            total_expected += item["price"] * item["quantity"]
            self.assert_test(
                result["success"] and result["data"].get("item_count", 0) > 0,
                f"Add cart item: {item['name']}",
                f"Cart total: ${result['data'].get('cart_total', 0):.2f}"
            )
        
        # Verify final cart state
        result = self.test_request("GET", "/session-test/state/cart")
        if result["success"]:
            self.assert_test(
                result["data"].get("item_count", 0) == len(items),
                "Verify cart item count",
                f"Expected: {len(items)}, Got: {result['data'].get('item_count', 0)}"
            )
            self.assert_test(
                abs(result["data"].get("total", 0) - total_expected) < 0.01,
                "Verify cart total calculation",
                f"Expected: ${total_expected:.2f}, Got: ${result['data'].get('total', 0):.2f}"
            )
    
    def test_advanced_decorators(self):
        """Test advanced decorators and guards."""
        self.log("🛡️ Testing advanced decorators and guards")
        
        # Re-authenticate as admin for guard tests
        auth_data = {
            "username": "admin_user",
            "role": "admin",
            "email": "admin@test.com",
            "email_verified": True
        }
        result = self.test_request("POST", "/session-test/authenticate", json=auth_data)
        
        # Test admin guard (should pass)
        result = self.test_request("GET", "/session-test/admin-only")
        self.assert_test(
            result["success"] and result["data"].get("admin_privileges", False),
            "Admin guard with admin user",
            f"User: {result['data'].get('user_id', 'N/A')}"
        )
        
        # Test verified guard (should pass)
        result = self.test_request("GET", "/session-test/verified-only")
        self.assert_test(
            result["success"] and result["data"].get("verified_privileges", False),
            "Verified guard with verified user",
            f"Email verified: {result['data'].get('email_verified', False)}"
        )
        
        # Test context managers
        result = self.test_request("POST", "/session-test/context-manager")
        if result["success"]:
            results = result["data"].get("results", [])
            self.assert_test(
                "ensure_context_success" in results,
                "SessionContext.ensure() context manager",
                "Context manager executed successfully"
            )
            self.assert_test(
                "auth_context_success" in results,
                "SessionContext.authenticated() context manager",
                "Authenticated context manager executed"
            )
        
        # Test with non-admin user
        auth_data["role"] = "user"
        self.test_request("POST", "/session-test/authenticate", json=auth_data)
        
        # Test admin guard (should fail)
        result = self.test_request("GET", "/session-test/admin-only")
        self.assert_test(
            not result["success"] and result["status_code"] == 403,
            "Admin guard with non-admin user",
            "Should return 403 for non-admin user"
        )
    
    def test_session_id_operations(self):
        """Test session ID operations and lifecycle."""
        self.log("🆔 Testing session ID operations")
        
        # Test session ID operations
        result = self.test_request("GET", "/session-test/id-operations")
        if result["success"]:
            data = result["data"]
            current_id = data.get("current_session_id", "")
            
            self.assert_test(
                current_id.startswith("sess_"),
                "Session ID format validation",
                f"ID starts with sess_: {current_id[:20]}..."
            )
            
            test_ids = data.get("test_ids", [])
            self.assert_test(
                len(test_ids) == 3 and all(tid.get("starts_with_sess", False) for tid in test_ids),
                "Session ID generation",
                f"Generated {len(test_ids)} valid IDs"
            )
            
            parse_test = data.get("parse_test", {})
            self.assert_test(
                parse_test.get("success", False),
                "Session ID parsing",
                "ID parsed and validated successfully"
            )
        
        # Test session rotation (requires authentication)
        self.test_request("POST", "/session-test/authenticate", json={
            "username": "rotation_test_user",
            "role": "user"
        })
        
        result = self.test_request("POST", "/session-test/rotate-id")
        self.assert_test(
            result["success"] and "old_session_id" in result["data"],
            "Session ID rotation",
            f"Rotation requested for session"
        )
    
    def test_error_handling(self):
        """Test error handling and fault scenarios."""
        self.log("⚠️ Testing error handling")
        
        # Test session required fault
        # First clear authentication
        self.test_request("POST", "/session-test/logout")
        
        result = self.test_request("GET", "/session-test/require-session-test")
        # Note: This should pass because @session.require() without arguments 
        # should still work with any session, even unauthenticated ones
        
        # Test authentication required fault
        result = self.test_request("GET", "/session-test/require-auth-test")
        self.assert_test(
            not result["success"] and result["status_code"] == 403,
            "Authentication required fault",
            "Should return 403 when authentication required but not authenticated"
        )
        
        # Test error simulation
        error_types = [
            "session_expired",
            "session_invalid", 
            "concurrency_violation",
            "store_unavailable",
            "session_required",
            "auth_required"
        ]
        
        for error_type in error_types:
            result = self.test_request("POST", "/session-test/simulate-error", json={"error_type": error_type})
            self.assert_test(
                not result["success"],
                f"Error simulation: {error_type}",
                f"Status: {result.get('status_code', 'N/A')}"
            )
        
        # Test no error simulation
        result = self.test_request("POST", "/session-test/simulate-error", json={"error_type": "none"})
        self.assert_test(
            result["success"],
            "No error simulation",
            "Should succeed when no error type specified"
        )
    
    def test_performance(self):
        """Test performance and bulk operations."""
        self.log("⚡ Testing performance and bulk operations")
        
        # Test bulk operations with different sizes
        bulk_sizes = [10, 50, 100]
        
        for size in bulk_sizes:
            start_time = time.time()
            result = self.test_request("POST", "/session-test/bulk-operations", json={"count": size})
            end_time = time.time()
            
            duration = end_time - start_time
            
            if result["success"]:
                operations = result["data"].get("results", {}).get("operations_performed", 0)
                self.assert_test(
                    operations == size,
                    f"Bulk operations (n={size})",
                    f"Completed {operations} operations in {duration:.3f}s"
                )
            else:
                self.assert_test(False, f"Bulk operations (n={size})", f"Failed after {duration:.3f}s")
    
    def test_analytics(self):
        """Test analytics and tracking features."""
        self.log("📊 Testing analytics and tracking")
        
        # Test analytics state
        result = self.test_request("GET", "/session-test/analytics")
        if result["success"]:
            self.assert_test(
                result["data"].get("page_views", 0) > 0,
                "Analytics page view tracking",
                f"Page views: {result['data'].get('page_views', 0)}"
            )
        
        # Test custom event tracking
        events = [
            {"type": "user_action", "name": "button_click", "properties": {"button": "submit"}},
            {"type": "navigation", "name": "page_change", "properties": {"from": "/home", "to": "/test"}},
            {"type": "custom", "name": "test_event", "properties": {"test_id": "regression_001"}}
        ]
        
        for event in events:
            result = self.test_request("POST", "/session-test/analytics/event", json=event)
            self.assert_test(
                result["success"] and result["data"].get("event", {}).get("type") == event["type"],
                f"Track analytics event: {event['name']}",
                f"Event type: {event['type']}"
            )
        
        # Verify events were tracked
        result = self.test_request("GET", "/session-test/analytics")
        if result["success"]:
            total_events = result["data"].get("total_events", 0)
            self.assert_test(
                total_events >= len(events),
                "Verify analytics events accumulation",
                f"Total events tracked: {total_events}"
            )
    
    def test_cleanup(self):
        """Test cleanup operations."""
        self.log("🧹 Testing cleanup operations")
        
        # Test session cleanup
        result = self.test_request("DELETE", "/session-test/cleanup")
        self.assert_test(
            result["success"] and result["data"].get("cleared_keys", 0) > 0,
            "Session cleanup",
            f"Cleared {result['data'].get('cleared_keys', 0)} session keys"
        )
        
        # Verify cleanup worked
        result = self.test_request("GET", "/session-test/data")
        if result["success"]:
            remaining_keys = len(result["data"].get("data", {}))
            self.assert_test(
                remaining_keys == 0,
                "Verify session cleanup",
                f"Remaining keys after cleanup: {remaining_keys}"
            )
    
    def print_test_summary(self):
        """Print test summary and statistics."""
        self.log("📋 Test Summary")
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["status"] == "PASS")
        failed_tests = total_tests - passed_tests
        pass_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        print("\n" + "="*80)
        print("🎯 AQUILIA SESSIONS REGRESSION TEST RESULTS")
        print("="*80)
        print(f"Total Tests:     {total_tests}")
        print(f"Passed:          {passed_tests} ✅")
        print(f"Failed:          {failed_tests} ❌")
        print(f"Pass Rate:       {pass_rate:.1f}%")
        print(f"Session ID:      {self.current_session_id[:30] if self.current_session_id else 'N/A'}...")
        print(f"Test User:       {self.current_user_id or 'N/A'}")
        
        if failed_tests > 0:
            print("\n❌ FAILED TESTS:")
            for result in self.test_results:
                if result["status"] == "FAIL":
                    print(f"  • {result['test']}: {result['details']}")
        
        print("\n✅ PASSED TESTS:")
        for result in self.test_results:
            if result["status"] == "PASS":
                print(f"  • {result['test']}")
        
        print("="*80)
        
        if pass_rate == 100:
            print("🎉 ALL TESTS PASSED! Aquilia sessions are working perfectly.")
        elif pass_rate >= 90:
            print("🌟 EXCELLENT! Most tests passed with minor issues.")
        elif pass_rate >= 75:
            print("👍 GOOD! Majority of tests passed, some issues to address.")
        else:
            print("⚠️ NEEDS ATTENTION! Multiple test failures detected.")
        
        return pass_rate == 100


def main():
    """Main test runner."""
    print("🚀 Aquilia Sessions Comprehensive Regression Test Suite")
    print("="*80)
    
    # Check if server is running
    try:
        response = requests.get("http://127.0.0.1:8000/session-test/info", timeout=5)
        print("✅ Server is running and responding")
    except requests.exceptions.RequestException:
        print("❌ ERROR: Server is not running or not accessible")
        print("Please start the Aquilia server with: python -m aquilia.cli run")
        sys.exit(1)
    
    # Run tests
    tester = SessionTester()
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()