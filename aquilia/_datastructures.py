"""
Core data structures for Aquilia Request handling.

Provides:
- MultiDict: Multi-value dictionary for query params and form data
- Headers: Case-insensitive header access
- URL: URL parsing and building
- ParsedContentType: Content-Type parsing helper
- Range: HTTP Range header representation
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import (
    Any, Dict, Iterator, List, Mapping, MutableMapping, 
    Optional, Tuple, Union
)
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from email.utils import parsedate_to_datetime


# ============================================================================
# MultiDict
# ============================================================================

class MultiDict(MutableMapping[str, List[str]]):
    """
    Dictionary that supports multiple values per key.
    
    Used for query parameters and form data where keys can repeat.
    """
    
    def __init__(self, items: Optional[Union[List[Tuple[str, str]], Mapping[str, Union[str, List[str]]]]] = None):
        self._data: Dict[str, List[str]] = {}
        
        if items:
            if isinstance(items, list):
                # List of tuples
                for key, value in items:
                    self.add(key, value)
            elif isinstance(items, dict):
                # Dictionary
                for key, value in items.items():
                    if isinstance(value, list):
                        self._data[key] = value.copy()
                    else:
                        self._data[key] = [value]
    
    def __getitem__(self, key: str) -> List[str]:
        """Get all values for a key."""
        return self._data[key]
    
    def __setitem__(self, key: str, value: Union[str, List[str]]) -> None:
        """Set values for a key (replaces existing)."""
        if isinstance(value, list):
            self._data[key] = value
        else:
            self._data[key] = [value]
    
    def __delitem__(self, key: str) -> None:
        """Delete all values for a key."""
        del self._data[key]
    
    def __iter__(self) -> Iterator[str]:
        """Iterate over keys."""
        return iter(self._data)
    
    def __len__(self) -> int:
        """Number of keys."""
        return len(self._data)
    
    def __repr__(self) -> str:
        return f"MultiDict({dict(self._data)})"
    
    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get first value for a key."""
        values = self._data.get(key)
        return values[0] if values else default
    
    def get_all(self, key: str) -> List[str]:
        """Get all values for a key."""
        return self._data.get(key, [])
    
    def add(self, key: str, value: str) -> None:
        """Add a value to a key (appends to list)."""
        if key in self._data:
            self._data[key].append(value)
        else:
            self._data[key] = [value]
    
    def items_list(self) -> List[Tuple[str, str]]:
        """Return all items as flat list of tuples."""
        result = []
        for key, values in self._data.items():
            for value in values:
                result.append((key, value))
        return result
    
    def to_dict(self, multi: bool = False) -> Dict[str, Union[str, List[str]]]:
        """
        Convert to regular dict.
        
        Args:
            multi: If True, return lists for all keys.
                   If False, return first value only.
        """
        if multi:
            return dict(self._data)
        else:
            return {k: v[0] for k, v in self._data.items() if v}


# ============================================================================
# Headers
# ============================================================================

@dataclass
class Headers:
    """
    Case-insensitive header access with raw preservation.
    
    Normalizes header names while preserving original casing.
    """
    
    raw: List[Tuple[bytes, bytes]] = field(default_factory=list)
    _index: Dict[str, List[Tuple[bytes, bytes]]] = field(default_factory=dict, init=False, repr=False)
    
    def __post_init__(self):
        """Build case-insensitive index."""
        self._index = {}
        for name, value in self.raw:
            key = name.decode("latin-1").lower()
            if key not in self._index:
                self._index[key] = []
            self._index[key].append((name, value))
    
    def get(self, name: str, default: Optional[str] = None) -> Optional[str]:
        """Get first value for header (case-insensitive)."""
        key = name.lower()
        pairs = self._index.get(key)
        if pairs:
            return pairs[0][1].decode("latin-1")
        return default
    
    def get_all(self, name: str) -> List[str]:
        """Get all values for header (case-insensitive)."""
        key = name.lower()
        pairs = self._index.get(key, [])
        return [value.decode("latin-1") for _, value in pairs]
    
    def has(self, name: str) -> bool:
        """Check if header exists."""
        return name.lower() in self._index
    
    def items(self) -> Iterator[Tuple[str, str]]:
        """Iterate over all headers."""
        for name, value in self.raw:
            yield name.decode("latin-1"), value.decode("latin-1")
    
    def keys(self) -> Iterator[str]:
        """Iterate over header names."""
        for name, _ in self.raw:
            yield name.decode("latin-1")
    
    def values(self) -> Iterator[str]:
        """Iterate over header values."""
        for _, value in self.raw:
            yield value.decode("latin-1")
    
    def __contains__(self, name: str) -> bool:
        """Check if header exists (case-insensitive)."""
        return self.has(name)
    
    def __getitem__(self, name: str) -> str:
        """Get header value (raises KeyError if not found)."""
        value = self.get(name)
        if value is None:
            raise KeyError(f"Header '{name}' not found")
        return value
    
    def __repr__(self) -> str:
        items = list(self.items())
        return f"Headers({items})"


# ============================================================================
# URL
# ============================================================================

@dataclass
class URL:
    """
    Parsed URL representation.
    
    Provides convenient access to URL components.
    """
    
    scheme: str
    host: str
    port: Optional[int] = None
    path: str = "/"
    query: str = ""
    fragment: str = ""
    username: Optional[str] = None
    password: Optional[str] = None
    
    @classmethod
    def parse(cls, url: str) -> "URL":
        """Parse URL string into components."""
        parsed = urlparse(url)
        
        # Parse netloc for host, port, username, password
        netloc = parsed.netloc
        username = parsed.username
        password = parsed.password
        
        # Extract host and port
        host = parsed.hostname or ""
        port = parsed.port
        
        return cls(
            scheme=parsed.scheme or "http",
            host=host,
            port=port,
            path=parsed.path or "/",
            query=parsed.query,
            fragment=parsed.fragment,
            username=username,
            password=password,
        )
    
    @property
    def netloc(self) -> str:
        """Build netloc string."""
        if self.username:
            auth = self.username
            if self.password:
                auth += f":{self.password}"
            netloc = f"{auth}@{self.host}"
        else:
            netloc = self.host
        
        if self.port:
            # Only include port if non-standard
            if not ((self.scheme == "http" and self.port == 80) or
                    (self.scheme == "https" and self.port == 443)):
                netloc += f":{self.port}"
        
        return netloc
    
    def __str__(self) -> str:
        """Build full URL string."""
        parts = (
            self.scheme,
            self.netloc,
            self.path,
            "",  # params (unused)
            self.query,
            self.fragment,
        )
        return urlunparse(parts)
    
    def replace(self, **kwargs) -> "URL":
        """Create new URL with replaced components."""
        data = {
            "scheme": self.scheme,
            "host": self.host,
            "port": self.port,
            "path": self.path,
            "query": self.query,
            "fragment": self.fragment,
            "username": self.username,
            "password": self.password,
        }
        data.update(kwargs)
        return URL(**data)
    
    def with_query(self, **params) -> "URL":
        """Create new URL with updated query parameters."""
        query = urlencode(params)
        return self.replace(query=query)


# ============================================================================
# ParsedContentType
# ============================================================================

@dataclass
class ParsedContentType:
    """
    Parsed Content-Type header.
    
    Extracts media type and parameters (e.g., charset).
    """
    
    media_type: str
    params: Dict[str, str] = field(default_factory=dict)
    
    @classmethod
    def parse(cls, content_type: Optional[str]) -> Optional["ParsedContentType"]:
        """Parse Content-Type header."""
        if not content_type:
            return None
        
        parts = content_type.split(";")
        media_type = parts[0].strip().lower()
        
        params = {}
        for part in parts[1:]:
            if "=" in part:
                key, value = part.split("=", 1)
                params[key.strip().lower()] = value.strip().strip('"')
        
        return cls(media_type=media_type, params=params)
    
    @property
    def charset(self) -> str:
        """Get charset parameter (default: utf-8)."""
        return self.params.get("charset", "utf-8")
    
    @property
    def boundary(self) -> Optional[str]:
        """Get boundary parameter (for multipart)."""
        return self.params.get("boundary")


# ============================================================================
# Range
# ============================================================================

@dataclass
class Range:
    """
    Parsed HTTP Range header.
    
    Represents byte range requests.
    """
    
    unit: str = "bytes"
    ranges: List[Tuple[Optional[int], Optional[int]]] = field(default_factory=list)
    
    @classmethod
    def parse(cls, range_header: Optional[str]) -> Optional["Range"]:
        """
        Parse Range header.
        
        Examples:
            bytes=0-499
            bytes=500-999
            bytes=-500  (last 500 bytes)
            bytes=500-  (from byte 500 to end)
        """
        if not range_header:
            return None
        
        match = re.match(r"(\w+)=(.+)", range_header)
        if not match:
            return None
        
        unit, ranges_str = match.groups()
        ranges = []
        
        for range_spec in ranges_str.split(","):
            range_spec = range_spec.strip()
            if "-" not in range_spec:
                continue
            
            start_str, end_str = range_spec.split("-", 1)
            
            start = int(start_str) if start_str else None
            end = int(end_str) if end_str else None
            
            ranges.append((start, end))
        
        return cls(unit=unit, ranges=ranges)
    
    def __str__(self) -> str:
        """Build Range header string."""
        range_specs = []
        for start, end in self.ranges:
            if start is None:
                range_specs.append(f"-{end}")
            elif end is None:
                range_specs.append(f"{start}-")
            else:
                range_specs.append(f"{start}-{end}")
        
        return f"{self.unit}={','.join(range_specs)}"


# ============================================================================
# Utility Functions
# ============================================================================

def parse_date_header(date_str: Optional[str]) -> Optional[Any]:
    """
    Parse HTTP date header.
    
    Returns datetime object or None.
    """
    if not date_str:
        return None
    
    try:
        return parsedate_to_datetime(date_str)
    except (ValueError, TypeError):
        return None


def parse_authorization_header(auth_header: Optional[str]) -> Optional[Tuple[str, str]]:
    """
    Parse Authorization header.
    
    Returns (scheme, credentials) tuple or None.
    
    Examples:
        "Bearer token123" -> ("Bearer", "token123")
        "Basic dXNlcjpwYXNz" -> ("Basic", "dXNlcjpwYXNz")
    """
    if not auth_header:
        return None
    
    parts = auth_header.split(None, 1)
    if len(parts) != 2:
        return None
    
    return parts[0], parts[1]
