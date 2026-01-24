# Aquilia Test Routes - myapp

## What's Been Added

I've added comprehensive test routes to your Aquilia application to verify the server is working correctly.

### New Files Created

1. **`modules/mymod/test_routes.py`** - TestController with multiple test endpoints
2. **`test_routes.py`** - Python test script using requests library
3. **`test_routes.sh`** - Bash script using curl for quick testing

### Test Endpoints Added

#### TestController (`/test/*`)

- `GET /test/hello` - Simple hello world response
- `GET /test/info` - API information and available endpoints
- `GET /test/echo/{message}` - Echo back a message (path parameter test)
- `GET /test/health` - Health check endpoint
- `GET /test/headers` - Test custom response headers
- `GET /test/status/{code}` - Test different HTTP status codes
- `POST /test/data` - Test JSON body parsing

#### MymodController (`/mymod/*`)

Existing CRUD endpoints:
- `GET /mymod/` - List all items
- `POST /mymod/` - Create new item
- `GET /mymod/{id}` - Get item by ID
- `PUT /mymod/{id}` - Update item by ID
- `DELETE /mymod/{id}` - Delete item by ID

## How to Test

### Method 1: Using the Bash Script (Recommended)

```bash
cd /Users/kuroyami/PyProjects/Aquilia/myapp
chmod +x test_routes.sh
./test_routes.sh
```

### Method 2: Using the Python Script

```bash
cd /Users/kuroyami/PyProjects/Aquilia/myapp
pip install requests  # if not already installed
python test_routes.py
```

### Method 3: Manual curl Commands

```bash
# Test hello endpoint
curl http://localhost:8000/test/hello

# Test echo with parameter
curl http://localhost:8000/test/echo/HelloWorld

# Test POST with JSON
curl -X POST http://localhost:8000/test/data \
  -H "Content-Type: application/json" \
  -d '{"name":"test","value":123}'

# Test mymod endpoints
curl http://localhost:8000/mymod/
curl http://localhost:8000/mymod/1

# Create new item
curl -X POST http://localhost:8000/mymod/ \
  -H "Content-Type: application/json" \
  -d '{"name":"New Item"}'
```

## Important: Restart the Server

⚠️ **You need to restart your server** for the new routes to be registered!

The `runtime/app.py` has been updated to include:
```python
controllers = [
    "modules.mymod.controllers:MymodController",
    "modules.mymod.test_routes:TestController",
]
```

### To Restart:

1. Stop the current server (Ctrl+C)
2. Run: `aq run` or `python runtime/app.py`

## Expected Output

After restarting the server and running the tests, you should see:

```json
{
    "message": "Hello from Aquilia!",
    "status": "success",
    "controller": "TestController"
}
```

## Troubleshooting

If you get `{"error": "Not found"}`:
- Make sure the server has been restarted
- Check that `runtime/app.py` includes the TestController
- Verify the server is running on port 8000

If you get connection errors:
- Ensure the server is running: `ps aux | grep python | grep app.py`
- Check the port: `lsof -i :8000`
- Try: `curl http://localhost:8000/test/hello`

## Route Details

### Path Parameters

Routes like `/test/echo/«message:str»` use Aquilia's pattern syntax:
- `«message:str»` - String parameter
- `«id:int»` - Integer parameter

### Response Format

All test routes return JSON with:
- Consistent structure
- Descriptive messages
- Proper HTTP status codes

### Custom Headers

The `/test/headers` endpoint demonstrates custom response headers:
```
X-Custom-Test: Aquilia-Test-Value
X-Request-ID: test-12345
```

## Next Steps

Once the server is restarted, run the test scripts to verify all routes are working correctly!
