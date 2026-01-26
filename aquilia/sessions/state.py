"""
Typed Session State for Aquilia.

Provides type-safe session state management with validation and auto-binding.

Example:
    >>> class CartState(SessionState):
    ...     items: List[str] = Field(default_factory=list)
    ...     total: float = 0.0
    
    >>> @stateful
    >>> async def add_to_cart(ctx, cart: CartState):
    ...     cart.items.append(item_id)
    ...     cart.total += price
"""

from typing import Any, Dict, Type, TypeVar, get_type_hints
from dataclasses import dataclass, field, fields, MISSING


T = TypeVar('T', bound='SessionState')


class Field:
    """Field descriptor for SessionState."""
    
    def __init__(self, default=MISSING, default_factory=MISSING):
        self.default = default
        self.default_factory = default_factory
    
    def __set_name__(self, owner, name):
        self.name = name
        self.private_name = f'_{name}'
    
    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return getattr(obj, self.private_name, self._get_default())
    
    def __set__(self, obj, value):
        setattr(obj, self.private_name, value)
    
    def _get_default(self):
        if self.default_factory is not MISSING:
            return self.default_factory()
        if self.default is not MISSING:
            return self.default
        return None


class SessionState:
    """
    Base class for typed session state.
    
    Provides type-safe access to session data with validation.
    
    Example:
        >>> class UserPreferences(SessionState):
        ...     theme: str = Field(default="light")
        ...     language: str = Field(default="en")
        ...     notifications: bool = Field(default=True)
        
        >>> prefs = UserPreferences(session_data)
        >>> prefs.theme = "dark"
        >>> prefs.language = "fr"
    """
    
    def __init__(self, data: Dict[str, Any]):
        """
        Initialize session state with data dictionary.
        
        Args:
            data: Session data dictionary (typically session.data)
        """
        self._data = data
        self._sync_from_data()
    
    def _sync_from_data(self):
        """Sync instance attributes from data dictionary."""
        hints = get_type_hints(self.__class__)
        
        for name, type_hint in hints.items():
            if name.startswith('_'):
                continue
            
            # Get value from data or use default
            if name in self._data:
                setattr(self, f'_{name}', self._data[name])
            else:
                # Use field default if available
                field_obj = getattr(self.__class__, name, None)
                if isinstance(field_obj, Field):
                    default_value = field_obj._get_default()
                    setattr(self, f'_{name}', default_value)
                    self._data[name] = default_value
    
    def _sync_to_data(self):
        """Sync instance attributes to data dictionary."""
        hints = get_type_hints(self.__class__)
        
        for name in hints.keys():
            if name.startswith('_'):
                continue
            
            value = getattr(self, f'_{name}', None)
            if value is not None:
                self._data[name] = value
    
    def __setattr__(self, name: str, value: Any):
        """Override setattr to sync to data dictionary."""
        if name.startswith('_'):
            # Private attributes
            super().__setattr__(name, value)
        else:
            # Public attributes - sync to data
            super().__setattr__(f'_{name}', value)
            if hasattr(self, '_data'):
                self._data[name] = value
    
    def __getattribute__(self, name: str):
        """Override getattribute for field access."""
        if name.startswith('_') or name in ('_sync_from_data', '_sync_to_data', 'get', 'to_dict', '__getitem__', '__setitem__'):
            return super().__getattribute__(name)
        
        # Check if it's a field
        try:
            cls_attr = getattr(self.__class__, name, None)
            if isinstance(cls_attr, Field):
                return super().__getattribute__(f'_{name}')
        except:
            pass
        
        return super().__getattribute__(name)
    
    def __getitem__(self, key: str) -> Any:
        return self._data.get(key)
        
    def __setitem__(self, key: str, value: Any):
        self._data[key] = value
        # Also sync to instance attr for consistency if it exists
        if hasattr(self, f'_{key}'):
            super().__setattr__(f'_{key}', value)

    def get(self, key: str, default: Any = None) -> Any:
        """Get state value with default."""
        return self._data.get(key, default)

    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary."""
        self._sync_to_data()
        return self._data.copy()
    
    def __repr__(self) -> str:
        hints = get_type_hints(self.__class__)
        fields_str = ", ".join(
            f"{name}={getattr(self, f'_{name}', None)}"
            for name in hints.keys()
            if not name.startswith('_')
        )
        return f"{self.__class__.__name__}({fields_str})"


# Example typed states

class CartState(SessionState):
    """Shopping cart session state."""
    items: list = Field(default_factory=list)
    total: float = Field(default=0.0)
    currency: str = Field(default="USD")


class UserPreferencesState(SessionState):
    """User preferences session state."""
    theme: str = Field(default="light")
    language: str = Field(default="en")
    notifications: bool = Field(default=True)
    timezone: str = Field(default="UTC")


__all__ = [
    "SessionState",
    "Field",
    "CartState",
    "UserPreferencesState",
]
