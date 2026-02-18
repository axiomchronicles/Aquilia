import subprocess, json, time, base64

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
    cmd = ["curl", "-s", "-o", "/tmp/resp.json", "-w", "%{http_code}", "-X", method,
           f"{BASE}{path}", "-H", f"Authorization: Bearer {token}"]
    if data is not None:
        cmd += ["-H", "Content-Type: application/json", "-d", json.dumps(data)]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    code = result.stdout.strip()
    try:
        with open("/tmp/resp.json") as f:
            resp = f.read()[:120]
    except:
        resp = "(no body)"
    ok = int(code) in expected_codes if code.isdigit() else False
    icon = "\u2705" if ok else "\u274C"
    if ok:
        passed += 1
    else:
        failed += 1
    print(f"{icon} {method:6s} {path:45s} -> {code}  {resp}")

total = passed + failed
print(f"\n{'='*60}")
print(f"  RESULTS: {passed} passed / {failed} failed / {total} total")
print(f"{'='*60}")
