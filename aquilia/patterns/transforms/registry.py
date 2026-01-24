"""
Transform function registry.
"""

from typing import Callable, Dict, Any


class TransformRegistry:
    """Registry of transform functions."""

    def __init__(self):
        self.transforms: Dict[str, Callable] = {}

    @classmethod
    def default(cls) -> "TransformRegistry":
        """Create registry with built-in transforms."""
        registry = cls()

        # Built-in transforms
        registry.register("lower", str.lower)
        registry.register("upper", str.upper)
        registry.register("strip", str.strip)
        registry.register("title", str.title)

        return registry

    def register(self, name: str, transform: Callable):
        """Register a custom transform."""
        self.transforms[name] = transform

    def get_transform(self, name: str) -> Callable:
        """Get transform by name."""
        if name not in self.transforms:
            raise ValueError(f"Unknown transform: {name}")
        return self.transforms[name]


def register_transform(name: str):
    """Decorator to register a custom transform."""
    def decorator(func: Callable) -> Callable:
        TransformRegistry.default().register(name, func)
        return func
    return decorator
