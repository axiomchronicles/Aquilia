"""Detailed curl-like integration test for the Aquilia starter page."""

import subprocess
import sys
import time
import os
import re
import urllib.request
import urllib.error

PYTHON = sys.executable
MYAPP = "/Users/kuroyami/PyProjects/Aquilia/myapp"


def main():
    proc = subprocess.Popen(
        [PYTHON, "-m", "aquilia.cli", "run", "--no-reload"],
        cwd=MYAPP,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    time.sleep(5)

    tests = [
        ("GET /  (HTML)", "http://127.0.0.1:8000/", {"Accept": "text/html"}),
        ("GET /  (JSON)", "http://127.0.0.1:8000/", {"Accept": "application/json"}),
        ("GET /blogs", "http://127.0.0.1:8000/blogs", {}),
        ("GET /nope (HTML)", "http://127.0.0.1:8000/nope", {"Accept": "text/html"}),
    ]

    print("=" * 60)
    print("  Aquilia Starter Page — curl Integration Tests")
    print("=" * 60)

    for name, url, headers in tests:
        try:
            req = urllib.request.Request(url, headers=headers)
            resp = urllib.request.urlopen(req, timeout=3)
            body = resp.read().decode("utf-8", errors="replace")
            ct = resp.headers.get("content-type", "")
            print(f"\n✅ {name}: HTTP {resp.status}  [{ct[:50]}]  ({len(body)} bytes)")
            if "html" in ct and len(body) > 100:
                m = re.search(r"<title>(.*?)</title>", body, re.IGNORECASE)
                if m:
                    print(f"   Title: {m.group(1)}")
            elif len(body) < 500:
                print(f"   Body: {body[:200]}")
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            ct = e.headers.get("content-type", "")
            print(f"\n{'✅' if e.code == 404 else '❌'} {name}: HTTP {e.code}  [{ct[:50]}]  ({len(body)} bytes)")
            if "html" in ct:
                m = re.search(r"<title>(.*?)</title>", body, re.IGNORECASE)
                if m:
                    print(f"   Title: {m.group(1)}")
            elif len(body) < 500:
                print(f"   Body: {body[:200]}")
        except Exception as e:
            print(f"\n❌ {name}: ERROR — {e}")

    print("\n" + "=" * 60)

    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
    print("🛑 Server stopped")


if __name__ == "__main__":
    main()
