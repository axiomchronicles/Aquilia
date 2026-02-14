"""Quick integration test: start server, curl /, verify starter page."""

import subprocess
import sys
import time
import urllib.request
import os
import signal

PYTHON = sys.executable
MYAPP = os.path.join(os.path.dirname(__file__), "myapp")


def main():
    # Start the server
    env = os.environ.copy()
    env["AQUILIA_ENV"] = "dev"
    env["AQUILIA_WORKSPACE"] = MYAPP

    proc = subprocess.Popen(
        [PYTHON, "-m", "aquilia.cli", "run", "--no-reload"],
        cwd=MYAPP,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    try:
        # Wait for server to start
        print("⏳ Waiting for server to start...")
        ready = False
        start = time.time()
        while time.time() - start < 15:
            try:
                req = urllib.request.Request(
                    "http://127.0.0.1:8000/",
                    headers={"Accept": "text/html"},
                )
                resp = urllib.request.urlopen(req, timeout=2)
                status = resp.status
                body = resp.read().decode("utf-8", errors="replace")
                ready = True
                break
            except Exception:
                time.sleep(0.5)

        if not ready:
            print("❌ Server did not start within 15 seconds")
            # Dump server output
            proc.terminate()
            proc.wait(timeout=5)
            out = proc.stdout.read()
            print("Server output:")
            print(out)
            return 1

        print(f"✅ GET / returned HTTP {status}")
        print(f"   Body length: {len(body)} bytes")

        # Check for welcome page markers
        if "Aquilia" in body and "<html" in body.lower():
            print("✅ Welcome page HTML detected!")
        elif "error" in body.lower() or "not found" in body.lower():
            print(f"❌ Got error response: {body[:200]}")
            return 1
        else:
            print(f"⚠️  Response (first 300 chars): {body[:300]}")

        # Also test JSON 404
        req2 = urllib.request.Request(
            "http://127.0.0.1:8000/nonexistent",
            headers={"Accept": "application/json"},
        )
        try:
            resp2 = urllib.request.urlopen(req2, timeout=2)
            print(f"   /nonexistent returned {resp2.status} (expected 404)")
        except urllib.error.HTTPError as e:
            print(f"✅ /nonexistent returned HTTP {e.code} (expected 404)")

        # Test /blogs
        try:
            req3 = urllib.request.Request("http://127.0.0.1:8000/blogs")
            resp3 = urllib.request.urlopen(req3, timeout=2)
            print(f"✅ GET /blogs returned HTTP {resp3.status}")
        except urllib.error.HTTPError as e:
            print(f"   GET /blogs returned HTTP {e.code}")
        except Exception as e:
            print(f"   GET /blogs error: {e}")

        return 0

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
        print("🛑 Server stopped")


if __name__ == "__main__":
    sys.exit(main())
