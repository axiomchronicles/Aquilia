"""
Constraint validator registry.
"""

from typing import Callable, Dict, Any


class ConstraintRegistry:
    """Registry of constraint validators."""

    def __init__(self):
        self.validators: Dict[str, Callable] = {}

    @classmethod
    def default(cls) -> "ConstraintRegistry":
        """Create registry with built-in constraints."""
        registry = cls()
        # Built-in constraints are handled in compiler
        return registry

    def register(self, name: str, validator: Callable):
        """Register a custom constraint validator."""
        self.validators[name] = validator

    def get_validator(self, name: str) -> Callable:
        """Get validator by name."""
        if name not in self.validators:
            raise ValueError(f"Unknown constraint: {name}")
        return self.validators[name]


def register_constraint(name: str):
    """Decorator to register a custom constraint."""
    def decorator(func: Callable) -> Callable:
        ConstraintRegistry.default().register(name, func)
        return func
    return decorator
