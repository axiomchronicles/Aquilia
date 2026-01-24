"""
Type registry and built-in type castors.
"""

from typing import Callable, Dict, Any
import uuid as uuid_lib
import json


class TypeRegistry:
    """Registry of type castors for pattern parameters."""

    def __init__(self):
        self.castors: Dict[str, Callable[[str], Any]] = {}

    @classmethod
    def default(cls) -> "TypeRegistry":
        """Create registry with built-in types."""
        registry = cls()

        # Built-in castors
        registry.register("str", lambda x: str(x))
        registry.register("int", lambda x: int(x))
        registry.register("float", lambda x: float(x))
        registry.register("bool", cls._cast_bool)
        registry.register("uuid", cls._cast_uuid)
        registry.register("slug", cls._cast_slug)
        registry.register("path", lambda x: x)  # Already a string
        registry.register("json", cls._cast_json)
        registry.register("any", lambda x: x)

        return registry

    @staticmethod
    def _cast_bool(value: str) -> bool:
        """Cast string to boolean."""
        lower = value.lower()
        if lower in ("true", "1", "yes", "on"):
            return True
        elif lower in ("false", "0", "no", "off"):
            return False
        raise ValueError(f"Invalid boolean value: {value}")

    @staticmethod
    def _cast_uuid(value: str) -> uuid_lib.UUID:
        """Cast string to UUID."""
        return uuid_lib.UUID(value)

    @staticmethod
    def _cast_slug(value: str) -> str:
        """Validate and return slug."""
        if not value.replace("-", "").replace("_", "").isalnum():
            raise ValueError(f"Invalid slug: {value}")
        return value

    @staticmethod
    def _cast_json(value: str) -> Any:
        """Parse JSON string."""
        return json.loads(value)

    def register(self, type_name: str, castor: Callable[[str], Any]):
        """Register a custom type castor."""
        self.castors[type_name] = castor

    def get_castor(self, type_name: str) -> Callable[[str], Any]:
        """Get castor for type."""
        if type_name not in self.castors:
            raise ValueError(f"Unknown type: {type_name}")
        return self.castors[type_name]

    def has_type(self, type_name: str) -> bool:
        """Check if type is registered."""
        return type_name in self.castors


def register_type(name: str, castor: Callable[[str], Any]):
    """Decorator to register a custom type."""
    def decorator(func: Callable) -> Callable:
        # Register in default registry
        TypeRegistry.default().register(name, castor)
        return func
    return decorator
