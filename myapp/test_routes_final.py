#!/usr/bin/env python3
"""Final route test — uses urllib (no subprocess/curl dependency)."""
import json, time, base64, urllib.request, urllib.error

BASE = "http://127.0.0.1:8000"

# Customer token
CTOKEN = "eyJzdWIiOiAiMSIsICJlbWFpbCI6ICJ0ZXN0dXNlckBuZXh1cy5pbyIsICJyb2xlIjogImN1c3RvbWVyIiwgImlhdCI6IDE3NzEzNjUyMDMsICJleHAiOiAxNzcxNDUxNjAzfQ=="

# Admin token
_ap = json.dumps({"sub":"99","email":"admin@nexus.io","role":"admin","iat":int(time.time()),"exp":int(time.time())+86400})
ATOKEN = base64.urlsafe_b64encode(_ap.encode()).decode().rstrip("=")

_uniq = str(int(time.time()))

# (method, path, data, token, expected_codes)
routes = [
    ("POST", "/users/auth/register", {"email":f"u{_uniq}@n.io","password":"Pass1234!","password_confirm":"Pass1234!","username":f"u{_uniq}"}, CTOKEN, [201]),
    ("POST", "/users/auth/login", {"email":"testuser@nexus.io","password":"Str0ng!Pass"}, CTOKEN, [200]),
    ("POST", "/users/auth/logout", None, CTOKEN, [200]),
    ("GET",  "/users/users/me", None, CTOKEN, [200]),
    ("PUT",  "/users/users/me", {"first_name":"Final","bio":"ok"}, CTOKEN, [200]),
    ("GET",  "/users/users/me/addresses", None, CTOKEN, [200]),
    ("POST", "/users/users/me/addresses", {"label":"Home","street_address":"123 Main","city":"NYC","state":"NY","postal_code":"10001","country":"US","is_default":True}, CTOKEN, [201]),
    ("GET",  "/users/users/me/sessions", None, CTOKEN, [200]),
    ("GET",  "/products/categories/", None, CTOKEN, [200]),
    ("GET",  "/products/categories/tree", None, CTOKEN, [200]),
    ("GET",  "/products/products/", None, CTOKEN, [200]),
    ("GET",  "/products/products/featured", None, CTOKEN, [200]),
    ("GET",  "/products/products/trending", None, CTOKEN, [200]),
    ("GET",  "/orders/cart/", None, CTOKEN, [200]),
    ("POST", "/orders/cart/items", {"product_id":1,"quantity":2}, CTOKEN, [200,201]),
    ("DELETE","/orders/cart/", None, CTOKEN, [200]),
    ("GET",  "/orders/orders/", None, CTOKEN, [200]),
    ("GET",  "/notifications/notifications/", None, CTOKEN, [200]),
    ("GET",  "/notifications/notifications/unread-count", None, CTOKEN, [200]),
    ("POST", "/notifications/notifications/mark-all-read", None, CTOKEN, [200]),
    ("GET",  "/analytics/analytics/dashboard", None, ATOKEN, [200]),
    ("GET",  "/analytics/analytics/revenue", None, ATOKEN, [200]),
    ("GET",  "/analytics/analytics/top-products", None, ATOKEN, [200]),
    ("GET",  "/analytics/recommendations/for-me", None, CTOKEN, [200]),
    ("GET",  "/analytics/recommendations/similar/1", None, CTOKEN, [200,404]),
    ("GET",  "/admin/admin/", None, ATOKEN, [200]),
    ("GET",  "/admin/admin/api/dashboard", None, ATOKEN, [200]),
    ("GET",  "/admin/admin/api/health", None, ATOKEN, [200,503]),
    ("GET",  "/testaquilia/", None, CTOKEN, [200]),
    ("POST", "/testaquilia/", {"name":"test item","value":42}, CTOKEN, [201]),
]

passed = failed = 0
for method, path, data, token, expected_codes in routes:
    url = f"{BASE}{path}"
    headers = {"Authorization": f"Bearer {token}"}
    body_bytes = None
    if data is not None:
        headers["Content-Type"] = "application/json"
        body_bytes = json.dumps(data).encode()

    req = urllib.request.Request(url, data=body_bytes, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        code = resp.status
        resp_body = resp.read().decode()[:120]
    except urllib.error.HTTPError as e:
        code = e.code
        resp_body = e.read().decode()[:120]
    except Exception as e:
        code = 0
        resp_body = str(e)[:120]

    ok = code in expected_codes
    icon = "\u2705" if ok else "\u274C"
    if ok:
        passed += 1
    else:
        failed += 1
    print(f"{icon} {method:6s} {path:46s} -> {code}  {resp_body}")

print()
print("=" * 60)
print(f"  RESULTS: {passed} passed / {failed} failed / {len(routes)} total")
print("=" * 60)
