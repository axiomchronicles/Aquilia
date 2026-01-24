#!/bin/bash
# Quick test script for Aquilia routes using curl

BASE_URL="http://localhost:8000"

echo "=================================================="
echo "  Aquilia Route Tests"
echo "=================================================="

echo -e "\n1. Testing /test/hello"
curl -s "$BASE_URL/test/hello" | python3 -m json.tool

echo -e "\n2. Testing /test/info"
curl -s "$BASE_URL/test/info" | python3 -m json.tool

echo -e "\n3. Testing /test/echo/HelloAquilia"
curl -s "$BASE_URL/test/echo/HelloAquilia" | python3 -m json.tool

echo -e "\n4. Testing /test/health"
curl -s "$BASE_URL/test/health" | python3 -m json.tool

echo -e "\n5. Testing /test/headers (check custom headers)"
curl -s -v "$BASE_URL/test/headers" 2>&1 | grep -E "(< X-|message)"

echo -e "\n6. Testing /test/status/200"
curl -s "$BASE_URL/test/status/200" | python3 -m json.tool

echo -e "\n7. Testing POST /test/data"
curl -s -X POST "$BASE_URL/test/data" \
  -H "Content-Type: application/json" \
  -d '{"name":"test","value":123}' | python3 -m json.tool

echo -e "\n8. Testing /mymod/ (list)"
curl -s "$BASE_URL/mymod/" | python3 -m json.tool

echo -e "\n9. Testing /mymod/1 (get by id)"
curl -s "$BASE_URL/mymod/1" | python3 -m json.tool

echo -e "\n10. Testing POST /mymod/ (create)"
curl -s -X POST "$BASE_URL/mymod/" \
  -H "Content-Type: application/json" \
  -d '{"name":"New Item"}' | python3 -m json.tool

echo -e "\n=================================================="
echo "  Tests Complete!"
echo "=================================================="
