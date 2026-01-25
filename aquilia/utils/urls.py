"""
URL Utilities for Aquilia.
"""

def join_paths(*parts: str) -> str:
    """
    Robustly join URL path segments.
    
    Handles:
    - Multiple slashes (//) -> /
    - Trailing/leading slashes
    - Empty segments
    
    Example:
        join_paths("/api/", "/v1", "users/") -> "/api/v1/users"
    """
    clean_parts = []
    
    for i, part in enumerate(parts):
        if not part:
            continue
            
        # Strip all slashes
        clean = part.strip("/")
        
        if clean:
            clean_parts.append(clean)
            
    # Join with /
    joined = "/" + "/".join(clean_parts)
    
    # Preserve trailing slash if specifically present in the LAST non-empty part
    # AND it's not the root
    if parts and parts[-1].endswith("/") and joined != "/":
        joined += "/"
        
    return joined

def normalize_path(path: str) -> str:
    """Normalize a URL path."""
    if not path:
        return "/"
    
    # Replace multiple slashes
    while "//" in path:
        path = path.replace("//", "/")
        
    return path
