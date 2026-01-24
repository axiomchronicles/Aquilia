"""
Test routes for mymod module - Additional test endpoints.
"""

from aquilia import Controller, GET, POST, RequestCtx, Response


class TestController(Controller):
    """Test endpoints for API verification."""
    
    prefix = "/test"
    tags = ["test"]
    
    @GET("/hello")
    async def hello(self, ctx: RequestCtx):
        """Simple hello world test endpoint."""
        return Response.json({
            "message": "Hello from Aquilia!",
            "status": "success",
            "controller": "TestController"
        })
    
    @GET("/echo/«message:str»")
    async def echo(self, ctx: RequestCtx, message: str):
        """Echo back a message with path parameter."""
        return Response.json({
            "echo": message,
            "length": len(message),
            "type": "path_param"
        })
    
    @POST("/data")
    async def post_data(self, ctx: RequestCtx):
        """Test POST with JSON body."""
        try:
            data = await ctx.json()
            return Response.json({
                "received": data,
                "keys": list(data.keys()) if isinstance(data, dict) else None,
                "status": "processed"
            })
        except Exception as e:
            return Response.json({
                "error": str(e),
                "status": "failed"
            }, status=400)
    
    @GET("/status/«code:int»")
    async def status_code(self, ctx: RequestCtx, code: int):
        """Test different HTTP status codes."""
        messages = {
            200: "OK",
            201: "Created",
            400: "Bad Request",
            404: "Not Found",
            500: "Internal Server Error"
        }
        return Response.json({
            "code": code,
            "message": messages.get(code, "Unknown Status")
        }, status=code)
    
    @GET("/headers")
    async def headers(self, ctx: RequestCtx):
        """Test custom response headers."""
        response = Response.json({
            "message": "Check the headers!",
            "custom_header": "X-Custom-Test"
        })
        response.headers["X-Custom-Test"] = "Aquilia-Test-Value"
        response.headers["X-Request-ID"] = "test-12345"
        return response
    
    @GET("/health")
    async def health(self, ctx: RequestCtx):
        """Health check endpoint."""
        return Response.json({
            "status": "healthy",
            "service": "test",
            "controller": "TestController",
            "timestamp": "2026-01-24"
        })
    
    @GET("/info")
    async def info(self, ctx: RequestCtx):
        """Get API info."""
        return Response.json({
            "api": "Aquilia Test API",
            "version": "1.0.0",
            "endpoints": [
                "GET /test/hello",
                "GET /test/echo/{message}",
                "POST /test/data",
                "GET /test/status/{code}",
                "GET /test/headers",
                "GET /test/health",
                "GET /test/info"
            ]
        })
