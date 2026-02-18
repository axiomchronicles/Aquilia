#!/usr/bin/env python3
"""
CRM Route Integration Tests
============================
Tests every route in the CRM application against a running server.
Each test opens and closes its own connection to avoid stale connections.

Usage:
    python3 test_routes.py          # requires server running on :8000
"""

import http.client
import json
import sys
import time


HOST = "127.0.0.1"
PORT = 8000
TIMEOUT = 10


def _request(method: str, path: str, body: dict | None = None, headers: dict | None = None) -> tuple:
    """Make an HTTP request and return (status, headers_dict, body_str)."""
    conn = http.client.HTTPConnection(HOST, PORT, timeout=TIMEOUT)
    try:
        hdrs = {"Content-Type": "application/json", "Accept": "application/json"}
        if headers:
            hdrs.update(headers)
        payload = json.dumps(body).encode() if body else None
        conn.request(method, path, body=payload, headers=hdrs)
        resp = conn.getresponse()
        status = resp.status
        resp_headers = {k.lower(): v for k, v in resp.getheaders()}
        resp_body = resp.read().decode("utf-8", errors="replace")
        return status, resp_headers, resp_body
    except Exception as e:
        return -1, {}, str(e)
    finally:
        conn.close()


def _json_body(body_str: str) -> dict | None:
    try:
        return json.loads(body_str)
    except (json.JSONDecodeError, ValueError):
        return None


# ═══════════════════════════════════════════════════════════════════
# Test definitions: (name, method, path, expected_status, body, check_fn)
# ═══════════════════════════════════════════════════════════════════

def _is_html(body: str) -> bool:
    return "<html" in body.lower() or "<!doctype" in body.lower()


TESTS: list[tuple] = []


def test(name, method, path, expected, body=None, check=None):
    TESTS.append((name, method, path, expected, body, check))


# ── Health ──────────────────────────────────────────────────────────
test("Health endpoint", "GET", "/health", 200)

# ── Root redirect ──────────────────────────────────────────────────
test("Root redirects to dashboard", "GET", "/", 302)

# ── Dashboard ──────────────────────────────────────────────────────
test("Dashboard page (HTML)", "GET", "/dashboard/", 200,
     check=lambda s, h, b: _is_html(b))
test("Dashboard API stats", "GET", "/dashboard/api/stats", 200,
     check=lambda s, h, b: _json_body(b) is not None)

# ── Auth pages ─────────────────────────────────────────────────────
test("Auth login page", "GET", "/auth/login", 200,
     check=lambda s, h, b: _is_html(b))
test("Auth register page", "GET", "/auth/register", 200,
     check=lambda s, h, b: _is_html(b))
test("Auth profile (no session → redirect)", "GET", "/auth/profile", 302)

# ── Auth API ───────────────────────────────────────────────────────
test("Auth API — list users", "GET", "/auth/api/users", 200,
     check=lambda s, h, b: isinstance(_json_body(b), list) or (isinstance(_json_body(b), dict) and "users" in str(_json_body(b)).lower()))

test("Auth API — register new user", "POST", "/auth/api/register", 201,
     body={
         "email": f"test_{int(time.time())}@crm.test",
         "password": "Str0ng!Pass",
         "first_name": "Test",
         "last_name": "User",
     })

test("Auth API — login with seeded user", "POST", "/auth/api/login", 200,
     body={"email": "admin@crm.local", "password": "admin123"})

test("Auth API — login bad creds", "POST", "/auth/api/login", [401, 500],
     body={"email": "admin@crm.local", "password": "wrong"})

test("Auth API — logout", "POST", "/auth/api/logout", 200)
test("Auth API — me (no session)", "GET", "/auth/api/me", 401)

# ── Contacts pages ─────────────────────────────────────────────────
test("Contacts list page", "GET", "/contacts/", 200,
     check=lambda s, h, b: _is_html(b))
test("Contacts new page", "GET", "/contacts/new", 200,
     check=lambda s, h, b: _is_html(b))
test("Contact detail page (id=1)", "GET", "/contacts/1", 200,
     check=lambda s, h, b: _is_html(b))
test("Contact edit page (id=1)", "GET", "/contacts/1/edit", 200,
     check=lambda s, h, b: _is_html(b))

# ── Contacts API ───────────────────────────────────────────────────
test("Contacts API — list", "GET", "/contacts/api/", 200,
     check=lambda s, h, b: _json_body(b) is not None)
test("Contacts API — get by id", "GET", "/contacts/api/1", 200,
     check=lambda s, h, b: _json_body(b) is not None)
test("Contacts API — stats", "GET", "/contacts/api/stats", 200)
test("Contacts API — create", "POST", "/contacts/api/", 201,
     body={
         "first_name": "RouteTest",
         "last_name": "Contact",
         "email": f"routetest_{int(time.time())}@crm.test",
     })

# ── Companies pages ────────────────────────────────────────────────
test("Companies list page", "GET", "/companies/", 200,
     check=lambda s, h, b: _is_html(b))
test("Companies new page", "GET", "/companies/new", 200,
     check=lambda s, h, b: _is_html(b))
test("Company detail page (id=1)", "GET", "/companies/1", 200,
     check=lambda s, h, b: _is_html(b))

# ── Companies API ──────────────────────────────────────────────────
test("Companies API — list", "GET", "/companies/api/", 200)
test("Companies API — get by id", "GET", "/companies/api/1", 200)
test("Companies API — stats", "GET", "/companies/api/stats", 200)

# ── Deals pages ────────────────────────────────────────────────────
test("Deals list page", "GET", "/deals/", 200,
     check=lambda s, h, b: _is_html(b))
test("Deals new page", "GET", "/deals/new", 200,
     check=lambda s, h, b: _is_html(b))
test("Deal detail page (id=1)", "GET", "/deals/1", 200,
     check=lambda s, h, b: _is_html(b))

# ── Deals API ──────────────────────────────────────────────────────
test("Deals API — list", "GET", "/deals/api/", 200)
test("Deals API — get by id", "GET", "/deals/api/1", 200)
test("Deals API — pipeline", "GET", "/deals/api/pipeline", 200)
test("Deals API — stats", "GET", "/deals/api/stats", 200)

# ── Tasks pages ────────────────────────────────────────────────────
test("Tasks list page", "GET", "/tasks/", 200,
     check=lambda s, h, b: _is_html(b))
test("Tasks new page", "GET", "/tasks/new", 200,
     check=lambda s, h, b: _is_html(b))
test("Task detail page (id=1)", "GET", "/tasks/1", 200,
     check=lambda s, h, b: _is_html(b))

# ── Tasks API ──────────────────────────────────────────────────────
test("Tasks API — list", "GET", "/tasks/api/", 200)
test("Tasks API — get by id", "GET", "/tasks/api/1", 200)
test("Tasks API — stats", "GET", "/tasks/api/stats", 200)

# ── Mail pages ─────────────────────────────────────────────────────
test("Mail inbox page", "GET", "/mail/", 200,
     check=lambda s, h, b: _is_html(b))
test("Mail compose page", "GET", "/mail/compose", 200,
     check=lambda s, h, b: _is_html(b))


# ═══════════════════════════════════════════════════════════════════
# Runner
# ═══════════════════════════════════════════════════════════════════

def main():
    passed = 0
    failed = 0
    errors: list[str] = []

    print(f"\n{'='*70}")
    print(f"  CRM Route Tests — {len(TESTS)} routes")
    print(f"{'='*70}\n")

    for name, method, path, expected, body, check in TESTS:
        status, headers, resp_body = _request(method, path, body)

        # expected can be a single int or a list of acceptable statuses
        expected_list = expected if isinstance(expected, list) else [expected]

        ok = status in expected_list
        if ok and check:
            try:
                ok = check(status, headers, resp_body)
            except Exception:
                ok = False

        if ok:
            passed += 1
            print(f"  ✅  {name}  [{method} {path}] → {status}")
        else:
            failed += 1
            # Summarize error body
            detail = ""
            jb = _json_body(resp_body)
            if jb:
                detail = json.dumps(jb, indent=None)[:200]
            else:
                detail = resp_body[:200].replace("\n", " ")
            err_msg = f"  ❌  {name}  [{method} {path}] → {status} (expected {expected})"
            if detail:
                err_msg += f"\n      {detail}"
            print(err_msg)
            errors.append(err_msg)

    print(f"\n{'='*70}")
    print(f"  Results: {passed} passed, {failed} failed, {len(TESTS)} total")
    print(f"{'='*70}")

    if errors:
        print(f"\n  Failed Tests:\n")
        for e in errors:
            print(e)
        print()

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
