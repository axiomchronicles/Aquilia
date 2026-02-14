"""
Static file serving controller.
"""

from aquilia import Controller, GET, RequestCtx, Response
from pathlib import Path

class StaticFilesController(Controller):
    """Serve static files (CSS, JS, images)."""
    
    prefix = "/static"
    tags = ["static"]
    
    @GET("/{filepath:path}")
    async def serve_static(self, ctx: RequestCtx, filepath: str):
        """
        Serve static files.
        
        GET /static/css/chat.css
        GET /static/js/chat.js
        """
        # Security: prevent directory traversal
        if ".." in filepath or filepath.startswith("/"):
            return Response.json({"error": "Invalid path"}, status=400)
        
        # Resolve file path
        static_root = Path("static")
        file_path = static_root / filepath
        
        if not file_path.exists() or not file_path.is_file():
            return Response.json({"error": "File not found"}, status=404)
        
        # Determine content type
        content_types = {
            ".css": "text/css",
            ".js": "application/javascript",
            ".json": "application/json",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".svg": "image/svg+xml",
            ".ico": "image/x-icon",
            ".woff": "font/woff",
            ".woff2": "font/woff2",
            ".ttf": "font/ttf",
            ".eot": "application/vnd.ms-fontobject",
        }
        
        ext = file_path.suffix.lower()
        content_type = content_types.get(ext, "application/octet-stream")
        
        # Read and return file
        try:
            with open(file_path, "rb") as f:
                content = f.read()
            
            return Response(
                content=content,
                status=200,
                headers={"content-type": content_type},
            )
        except Exception as e:
            return Response.json({"error": f"Error reading file: {e}"}, status=500)
