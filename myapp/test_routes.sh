#!/bin/zsh
set -e

BASE="http://127.0.0.1:8000"
TOKEN="eyJzdWIiOiAiMSIsICJlbWFpbCI6ICJ0ZXN0dXNlckBuZXh1cy5pbyIsICJyb2xlIjogImN1c3RvbWVyIiwgImlhdCI6IDE3NzEzNjUyMDMsICJleHAiOiAxNzcxNDUxNjAzfQ=="
AUTH="Authorization: Bearer $TOKEN"
CT="Content-Type: application/json"
PASS=0
FAIL=0
TOTAL=0

test_route() {
    local method=$1
    local path=$2
    local data=$3
    local expect_code=${4:-200}
    TOTAL=$((TOTAL+1))
    
    if [[ -n "$data" ]]; then
        code=$(curl -s -o /tmp/resp.json -w "%{http_code}" -X "$method" "$BASE$path" -H "$AUTH" -H "$CT" -d "$data" 2>/dev/null)
    else
        code=$(curl -s -o /tmp/resp.json -w "%{http_code}" -X "$method" "$BASE$path" -H "$AUTH" 2>/dev/null)
    fi
    
    resp=$(cat /tmp/resp.json | head -c 120)
    
    if [[ "$code" =~ ^($expect_code|2[0-9][0-9])$ ]]; then
        echo "✅ $method $path → $code  $resp"
        PASS=$((PASS+1))
    else
        echo "❌ $method $path → $code  $resp"
        FAIL=$((FAIL+1))
    fi
}

echo "═══════════════════════════════════════════════════════"
echo "  NEXUS PLATFORM — COMPREHENSIVE ROUTE TESTING"
echo "═══════════════════════════════════════════════════════"

echo ""
echo "── AUTH ROUTES ──────────────────────────────────────"
test_route POST "/users/auth/register" '{"email":"test3@nexus.io","password":"Pass1234!","password_confirm":"Pass1234!","username":"testuser3"}'
test_route POST "/users/auth/login" '{"email":"testuser@nexus.io","password":"Str0ng!Pass"}'
test_route POST "/users/auth/logout" ""
test_route POST "/users/auth/password/change" '{"current_password":"Str0ng!Pass","new_password":"NewStr0ng!","new_password_confirm":"NewStr0ng!"}'

echo ""
echo "── USER ROUTES ─────────────────────────────────────"
test_route GET "/users/users/me"
test_route PUT "/users/users/me" '{"first_name":"Updated","bio":"Testing"}'
test_route GET "/users/users/me/addresses"
test_route POST "/users/users/me/addresses" '{"label":"Home","street_address":"123 Main St","city":"Springfield","state":"IL","postal_code":"62701","country":"US","is_default":true}'
test_route GET "/users/users/me/sessions"

echo ""
echo "── PRODUCT ROUTES (Public) ─────────────────────────"
test_route GET "/products/categories/"
test_route GET "/products/categories/tree"
test_route GET "/products/products/"
test_route GET "/products/products/featured"
test_route GET "/products/products/trending"

echo ""
echo "── PRODUCT ROUTES (Auth) ───────────────────────────"
test_route POST "/products/categories/" '{"name":"Electronics","slug":"electronics","description":"Electronic goods"}'
test_route POST "/products/products/" '{"name":"Test Product","slug":"test-product","description":"A test","price":29.99,"sku":"TST-001","category_id":1,"status":"active"}'

echo ""
echo "── ORDER ROUTES ────────────────────────────────────"
test_route GET "/orders/cart/"
test_route POST "/orders/cart/items" '{"product_id":1,"quantity":2}'
test_route DELETE "/orders/cart/"
test_route POST "/orders/orders/checkout" '{"items":[{"product_id":1,"quantity":1}],"shipping_address":{"street":"123 Main","city":"NYC","state":"NY","postal_code":"10001","country":"US"}}'
test_route GET "/orders/orders/"

echo ""
echo "── NOTIFICATION ROUTES ─────────────────────────────"
test_route GET "/notifications/notifications/"
test_route GET "/notifications/notifications/unread-count"
test_route POST "/notifications/notifications/mark-all-read"

echo ""
echo "── ANALYTICS ROUTES ────────────────────────────────"
test_route GET "/analytics/analytics/dashboard"
test_route GET "/analytics/analytics/revenue"
test_route GET "/analytics/analytics/top-products"
test_route GET "/analytics/analytics/orders/distribution"
test_route GET "/analytics/recommendations/for-me"
test_route GET "/analytics/recommendations/similar/1"

echo ""
echo "── ADMIN ROUTES ────────────────────────────────────"
test_route GET "/admin/admin/"
test_route GET "/admin/admin/api/dashboard"
test_route GET "/admin/admin/api/health"

echo ""
echo "── TESTAQUILIA ROUTES ──────────────────────────────"
test_route GET "/testaquilia/"
test_route POST "/testaquilia/" '{"name":"test item","value":42}'

echo ""
echo "═══════════════════════════════════════════════════════"
echo "  RESULTS: $PASS passed / $FAIL failed / $TOTAL total"
echo "═══════════════════════════════════════════════════════"
