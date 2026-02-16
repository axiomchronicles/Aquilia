#!/usr/bin/env python3
"""
Test all MLOps routes using requests library.

Run the server first:
    python -m aquilia.cli run

Then run this test script:
    python myapp/test_mlops_routes.py
"""

import requests
import time
import json
from typing import Dict, Any

# Configuration
BASE_URL = "http://localhost:8000/mlops"
TIMEOUT = 10


class MLOpsRouteTest:
    """Test harness for MLOps endpoints."""
    
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()
        self.results = []
    
    def log(self, method: str, endpoint: str, status: int, success: bool, message: str = ""):
        """Log test result."""
        symbol = "✓" if success else "✗"
        color = "\033[92m" if success else "\033[91m"
        reset = "\033[0m"
        
        result = {
            "method": method,
            "endpoint": endpoint,
            "status": status,
            "success": success,
            "message": message,
        }
        self.results.append(result)
        
        print(f"{color}{symbol}{reset} {method:6} {endpoint:35} [{status}] {message}")
    
    def test_get(self, endpoint: str, expected_status: int = 200) -> Dict[str, Any]:
        """Test GET endpoint."""
        url = f"{self.base_url}{endpoint}"
        try:
            response = self.session.get(url, timeout=TIMEOUT)
            success = response.status_code == expected_status
            
            self.log("GET", endpoint, response.status_code, success, 
                    response.json() if success else response.text[:50])
            
            return response.json() if success else {}
        except Exception as e:
            self.log("GET", endpoint, 0, False, str(e))
            return {}
    
    def test_post(self, endpoint: str, data: Dict[str, Any] = None, 
                  expected_status: int = 200) -> Dict[str, Any]:
        """Test POST endpoint."""
        url = f"{self.base_url}{endpoint}"
        try:
            response = self.session.post(url, json=data or {}, timeout=TIMEOUT)
            success = response.status_code == expected_status
            
            msg = ""
            if success and response.content:
                try:
                    result = response.json()
                    msg = json.dumps(result)[:100]
                except:
                    msg = response.text[:50]
            elif not success:
                msg = response.text[:100]
            
            self.log("POST", endpoint, response.status_code, success, msg)
            
            return response.json() if success and response.content else {}
        except Exception as e:
            self.log("POST", endpoint, 0, False, str(e))
            return {}
    
    def run_all_tests(self):
        """Execute all MLOps route tests."""
        print(f"\n{'='*80}")
        print(f"Testing MLOps Routes at {self.base_url}")
        print(f"{'='*80}\n")
        
        # ── Health Checks ────────────────────────────────────────────
        print("Health Checks:")
        self.test_get("/health")
        self.test_get("/healthz")
        self.test_get("/readyz")
        self.test_get("/metrics")
        print()
        
        # ── Training ─────────────────────────────────────────────────
        print("Training & Packaging:")
        train_result = self.test_post("/train", {
            "n_estimators": 100,
            "max_depth": 5,
            "test_size": 0.2,
        })
        
        pack_result = self.test_post("/pack", {
            "version": "v1.0.0",
        }, expected_status=201)
        print()
        
        # ── Deployment ───────────────────────────────────────────────
        print("Deployment:")
        deploy_result = self.test_post("/deploy", {
            "version": "v1.0.0",
        })
        
        # Wait a bit for deployment
        if deploy_result:
            time.sleep(1)
        print()
        
        # ── Inference ────────────────────────────────────────────────
        print("Inference:")
        predict_result = self.test_post("/predict", {
            "features": [5.1, 3.5, 1.4, 0.2],  # Iris setosa sample
        })
        
        batch_result = self.test_post("/predict/batch", {
            "samples": [
                [5.1, 3.5, 1.4, 0.2],  # setosa
                [6.7, 3.1, 4.7, 1.5],  # versicolor
                [6.3, 3.3, 6.0, 2.5],  # virginica
            ],
        })
        print()
        
        # ── Lineage ──────────────────────────────────────────────────
        print("Lineage:")
        self.test_get("/lineage")
        print()
        
        # ── Experiments ──────────────────────────────────────────────
        print("Experiments:")
        exp_result = self.test_post("/experiments", {
            "experiment_id": "iris_test_v1",
            "arms": [
                {"name": "baseline", "version": "v1.0.0", "weight": 0.5},
                {"name": "candidate", "version": "v1.1.0", "weight": 0.5},
            ],
            "description": "Test A/B experiment",
        }, expected_status=201)
        
        self.test_get("/experiments")
        
        self.test_post("/experiments/conclude", {
            "experiment_id": "iris_test_v1",
            "winner": "baseline",
        })
        print()
        
        # ── Cleanup ──────────────────────────────────────────────────
        print("Cleanup:")
        self.test_post("/undeploy")
        print()
        
        # ── Summary ──────────────────────────────────────────────────
        self.print_summary()
    
    def print_summary(self):
        """Print test summary."""
        total = len(self.results)
        passed = sum(1 for r in self.results if r["success"])
        failed = total - passed
        
        print(f"{'='*80}")
        print(f"Test Summary:")
        print(f"  Total:  {total}")
        print(f"  Passed: {passed} ✓")
        print(f"  Failed: {failed} {'✗' if failed > 0 else ''}")
        print(f"{'='*80}\n")
        
        if failed > 0:
            print("Failed tests:")
            for r in self.results:
                if not r["success"]:
                    print(f"  ✗ {r['method']} {r['endpoint']} - {r['message']}")
            print()


def main():
    """Main entry point."""
    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=2)
        if response.status_code != 200:
            print("⚠  Warning: Server might not be running properly")
    except requests.exceptions.ConnectionError:
        print("✗ Error: Cannot connect to server. Please start it with:")
        print("  python -m aquilia.cli run")
        return 1
    except Exception as e:
        print(f"✗ Error: {e}")
        return 1
    
    # Run tests
    tester = MLOpsRouteTest()
    tester.run_all_tests()
    
    # Return exit code
    failed = sum(1 for r in tester.results if not r["success"])
    return 1 if failed > 0 else 0


if __name__ == "__main__":
    exit(main())
