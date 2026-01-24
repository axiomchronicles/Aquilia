"""
Production-ready caching layer for compiled patterns.

Provides:
- Thread-safe LRU cache with TTL
- Pattern fingerprinting for cache keys
- Cache statistics and monitoring
- Invalidation strategies
"""

import threading
import time
import hashlib
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Callable
from collections import OrderedDict
from contextlib import contextmanager

from .compiler.compiler import CompiledPattern, PatternCompiler
from .compiler.parser import parse_pattern


@dataclass
class CacheStats:
    """Cache statistics for monitoring."""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    errors: int = 0
    total_compile_time: float = 0.0
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Export stats as dictionary."""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "errors": self.errors,
            "total_compile_time": self.total_compile_time,
            "hit_rate": self.hit_rate,
        }


@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    pattern: CompiledPattern
    created_at: float
    last_accessed: float
    access_count: int
    compile_time: float
    
    def is_expired(self, ttl: Optional[float]) -> bool:
        """Check if entry has expired."""
        if ttl is None:
            return False
        return time.time() - self.created_at > ttl


class PatternCache:
    """Thread-safe LRU cache for compiled patterns with TTL support."""
    
    def __init__(
        self,
        max_size: int = 1000,
        ttl: Optional[float] = None,
        enable_stats: bool = True,
    ):
        """
        Initialize pattern cache.
        
        Args:
            max_size: Maximum number of patterns to cache
            ttl: Time-to-live in seconds (None = no expiration)
            enable_stats: Enable statistics collection
        """
        self.max_size = max_size
        self.ttl = ttl
        self.enable_stats = enable_stats
        
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()
        self._stats = CacheStats()
        self._compiler: Optional[PatternCompiler] = None
    
    def _get_compiler(self) -> PatternCompiler:
        """Get or create compiler instance."""
        if self._compiler is None:
            self._compiler = PatternCompiler()
        return self._compiler
    
    def _fingerprint(self, pattern: str, **kwargs) -> str:
        """
        Generate cache key from pattern and context.
        
        Args:
            pattern: Pattern string
            **kwargs: Additional context (e.g., type_registry settings)
        
        Returns:
            Cache key fingerprint
        """
        # Include pattern and any context that affects compilation
        cache_input = f"{pattern}:{sorted(kwargs.items())}"
        return hashlib.sha256(cache_input.encode()).hexdigest()[:16]
    
    def get(
        self,
        pattern: str,
        **kwargs
    ) -> Optional[CompiledPattern]:
        """
        Get compiled pattern from cache.
        
        Args:
            pattern: Pattern string
            **kwargs: Additional context for fingerprinting
        
        Returns:
            Compiled pattern or None if not cached
        """
        key = self._fingerprint(pattern, **kwargs)
        
        with self._lock:
            entry = self._cache.get(key)
            
            if entry is None:
                if self.enable_stats:
                    self._stats.misses += 1
                return None
            
            # Check expiration
            if entry.is_expired(self.ttl):
                del self._cache[key]
                if self.enable_stats:
                    self._stats.evictions += 1
                    self._stats.misses += 1
                return None
            
            # Update LRU order
            self._cache.move_to_end(key)
            entry.last_accessed = time.time()
            entry.access_count += 1
            
            if self.enable_stats:
                self._stats.hits += 1
            
            return entry.pattern
    
    def put(
        self,
        pattern: str,
        compiled: CompiledPattern,
        compile_time: float = 0.0,
        **kwargs
    ):
        """
        Store compiled pattern in cache.
        
        Args:
            pattern: Pattern string
            compiled: Compiled pattern
            compile_time: Time taken to compile (seconds)
            **kwargs: Additional context for fingerprinting
        """
        key = self._fingerprint(pattern, **kwargs)
        now = time.time()
        
        with self._lock:
            # Evict LRU if at capacity
            if len(self._cache) >= self.max_size and key not in self._cache:
                self._cache.popitem(last=False)
                if self.enable_stats:
                    self._stats.evictions += 1
            
            entry = CacheEntry(
                pattern=compiled,
                created_at=now,
                last_accessed=now,
                access_count=0,
                compile_time=compile_time,
            )
            
            self._cache[key] = entry
            self._cache.move_to_end(key)
    
    def compile_with_cache(
        self,
        pattern: str,
        **kwargs
    ) -> CompiledPattern:
        """
        Compile pattern with caching.
        
        This is the main API for cached compilation.
        
        Args:
            pattern: Pattern string
            **kwargs: Additional context
        
        Returns:
            Compiled pattern (from cache or freshly compiled)
        
        Raises:
            PatternSyntaxError: Invalid pattern syntax
            PatternSemanticError: Invalid pattern semantics
        """
        # Try cache first
        cached = self.get(pattern, **kwargs)
        if cached is not None:
            return cached
        
        # Compile on miss
        start_time = time.time()
        
        try:
            ast = parse_pattern(pattern)
            compiler = self._get_compiler()
            compiled = compiler.compile(ast)
            
            compile_time = time.time() - start_time
            
            # Store in cache
            self.put(pattern, compiled, compile_time, **kwargs)
            
            if self.enable_stats:
                self._stats.total_compile_time += compile_time
            
            return compiled
            
        except Exception as e:
            if self.enable_stats:
                self._stats.errors += 1
            raise
    
    def invalidate(self, pattern: Optional[str] = None, **kwargs):
        """
        Invalidate cache entries.
        
        Args:
            pattern: Specific pattern to invalidate (None = clear all)
            **kwargs: Additional context for fingerprinting
        """
        with self._lock:
            if pattern is None:
                # Clear all
                self._cache.clear()
            else:
                # Clear specific pattern
                key = self._fingerprint(pattern, **kwargs)
                if key in self._cache:
                    del self._cache[key]
    
    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        with self._lock:
            return CacheStats(
                hits=self._stats.hits,
                misses=self._stats.misses,
                evictions=self._stats.evictions,
                errors=self._stats.errors,
                total_compile_time=self._stats.total_compile_time,
            )
    
    def reset_stats(self):
        """Reset statistics counters."""
        with self._lock:
            self._stats = CacheStats()
    
    @contextmanager
    def disabled(self):
        """Context manager to temporarily disable cache."""
        old_size = self.max_size
        self.max_size = 0
        try:
            yield
        finally:
            self.max_size = old_size
    
    def __len__(self) -> int:
        """Get current cache size."""
        with self._lock:
            return len(self._cache)
    
    def __contains__(self, pattern: str) -> bool:
        """Check if pattern is cached."""
        key = self._fingerprint(pattern)
        with self._lock:
            return key in self._cache


# Global cache instance
_global_cache: Optional[PatternCache] = None


def get_global_cache() -> PatternCache:
    """Get or create global cache instance."""
    global _global_cache
    if _global_cache is None:
        _global_cache = PatternCache()
    return _global_cache


def set_global_cache(cache: Optional[PatternCache]):
    """Set global cache instance."""
    global _global_cache
    _global_cache = cache


def compile_pattern(pattern: str, use_cache: bool = True, **kwargs) -> CompiledPattern:
    """
    Convenience function to compile patterns with optional caching.
    
    Args:
        pattern: Pattern string
        use_cache: Whether to use global cache
        **kwargs: Additional context
    
    Returns:
        Compiled pattern
    """
    if use_cache:
        cache = get_global_cache()
        return cache.compile_with_cache(pattern, **kwargs)
    else:
        ast = parse_pattern(pattern)
        compiler = PatternCompiler()
        return compiler.compile(ast)
