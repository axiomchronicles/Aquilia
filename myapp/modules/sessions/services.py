"""
Sessions Module - Services

Showcases:
- Cart business logic with session-backed storage
- Preferences management
- Wizard workflow with state tracking
"""

from typing import Dict, Any, List, Optional
from aquilia.di import service


@service(scope="request")
class CartService:
    """
    Shopping cart service.

    Request-scoped: works with the current request's session.
    Demonstrates session-backed state management.
    """

    def __init__(self):
        pass

    async def get_cart(self, session: dict) -> Dict[str, Any]:
        """Get current cart contents from session."""
        return {
            "items": session.get("cart_items", []),
            "total": session.get("cart_total", 0.0),
            "item_count": len(session.get("cart_items", [])),
            "currency": session.get("cart_currency", "USD"),
        }

    async def add_item(
        self,
        session: dict,
        product_id: str,
        name: str,
        price: float,
        quantity: int = 1,
    ) -> Dict[str, Any]:
        """Add item to cart."""
        items = session.get("cart_items", [])

        # Check if item already in cart
        for item in items:
            if item["product_id"] == product_id:
                item["quantity"] += quantity
                item["subtotal"] = item["price"] * item["quantity"]
                break
        else:
            items.append({
                "product_id": product_id,
                "name": name,
                "price": price,
                "quantity": quantity,
                "subtotal": price * quantity,
            })

        session["cart_items"] = items
        session["cart_total"] = sum(i["subtotal"] for i in items)

        return await self.get_cart(session)

    async def remove_item(self, session: dict, product_id: str) -> Dict[str, Any]:
        """Remove item from cart."""
        items = session.get("cart_items", [])
        items = [i for i in items if i["product_id"] != product_id]
        session["cart_items"] = items
        session["cart_total"] = sum(i["subtotal"] for i in items)
        return await self.get_cart(session)

    async def clear_cart(self, session: dict) -> Dict[str, Any]:
        """Clear entire cart."""
        session["cart_items"] = []
        session["cart_total"] = 0.0
        return await self.get_cart(session)

    async def apply_coupon(self, session: dict, code: str) -> Dict[str, Any]:
        """Apply discount coupon."""
        # Simple coupon logic
        coupons = {
            "SAVE10": 10.0,
            "SAVE20": 20.0,
            "HALF": 50.0,
        }

        discount = coupons.get(code.upper(), 0.0)
        if discount:
            session["coupon_code"] = code.upper()
            session["discount_percent"] = discount
        else:
            return {"error": "Invalid coupon code"}

        cart = await self.get_cart(session)
        cart["coupon_code"] = code.upper()
        cart["discount_percent"] = discount
        cart["discounted_total"] = cart["total"] * (1 - discount / 100)
        return cart


@service(scope="request")
class PreferencesService:
    """
    User preferences management.

    Demonstrates session-backed user settings.
    """

    DEFAULTS = {
        "theme": "light",
        "language": "en",
        "timezone": "UTC",
        "notifications": True,
        "items_per_page": 25,
    }

    async def get_preferences(self, session: dict) -> Dict[str, Any]:
        """Get all preferences with defaults."""
        prefs = {}
        for key, default in self.DEFAULTS.items():
            prefs[key] = session.get(f"pref_{key}", default)
        return prefs

    async def update_preferences(self, session: dict, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update specific preferences."""
        for key, value in updates.items():
            if key in self.DEFAULTS:
                session[f"pref_{key}"] = value
        return await self.get_preferences(session)

    async def reset_preferences(self, session: dict) -> Dict[str, Any]:
        """Reset all preferences to defaults."""
        for key in self.DEFAULTS:
            session.pop(f"pref_{key}", None)
        return await self.get_preferences(session)
