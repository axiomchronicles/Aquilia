"""
Sessions Module - Typed Session State

Showcases:
- SessionState with typed fields
- Field defaults and factories
- Multiple state schemas
- Cart and preferences patterns
"""

from aquilia.sessions import SessionState, Field


class CartState(SessionState):
    """
    Shopping cart session state.

    Demonstrates typed session fields with defaults.
    Each session gets its own CartState instance.
    """

    items: list = Field(default_factory=list)
    total: float = Field(default=0.0)
    currency: str = Field(default="USD")
    item_count: int = Field(default=0)
    coupon_code: str = Field(default="")
    discount_percent: float = Field(default=0.0)


class UserPreferencesState(SessionState):
    """
    User preferences stored in session.

    Demonstrates personalization via session state.
    """

    theme: str = Field(default="light")
    language: str = Field(default="en")
    timezone: str = Field(default="UTC")
    notifications_enabled: bool = Field(default=True)
    items_per_page: int = Field(default=25)
    sidebar_collapsed: bool = Field(default=False)


class WizardState(SessionState):
    """
    Multi-step form wizard state.

    Demonstrates using session to track progress
    through a multi-step workflow.
    """

    current_step: int = Field(default=1)
    total_steps: int = Field(default=4)
    completed_steps: list = Field(default_factory=list)
    form_data: dict = Field(default_factory=dict)
    is_complete: bool = Field(default=False)
