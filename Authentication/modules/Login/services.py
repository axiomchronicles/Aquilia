"""
Login module services (business logic).

Services contain the core business logic and are auto-wired
via dependency injection.
"""

from typing import Optional, List
from aquilia.di import service, Inject
from .serilizers import UserSerilizer

@service(scope="app")
class LoginService:
    """
    Service for Login business logic.

    This service is automatically registered with the DI container
    and can be injected into controllers.

    To inject dependencies, add type-annotated parameters to __init__:

        def __init__(self, db: AquiliaDatabase, auth: AuthManager):
            self.db = db
            self.auth = auth
    """

    def __init__(self, serilizer: UserSerilizer):
        ...