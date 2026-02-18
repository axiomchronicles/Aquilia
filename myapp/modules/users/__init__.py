"""
Users Module — User management, authentication, and authorization.

Components:
- Models: User, UserAddress, UserSession
- Services: UserService, AuthService
- Controllers: UserController, AuthController
- Serializers: Full CRUD + auth serializers
- Faults: User-specific error handling
- Middleware: Auth enforcement, RBAC, audit logging
"""

from .models import User, UserAddress, UserSession, UserRole
from .services import UserService, AuthService
from .controllers import UserController, AuthController
from .faults import (
    UserNotFoundFault,
    DuplicateEmailFault,
    InvalidCredentialsFault,
    InsufficientPermissionsFault,
)

__all__ = [
    "User", "UserAddress", "UserSession", "UserRole",
    "UserService", "AuthService",
    "UserController", "AuthController",
    "UserNotFoundFault", "DuplicateEmailFault",
    "InvalidCredentialsFault", "InsufficientPermissionsFault",
]
