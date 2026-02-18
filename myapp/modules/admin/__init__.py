"""
Admin Module — Dashboard, system management, and bulk operations.

Components:
- Services: AdminService
- Controllers: AdminDashboardController (HTML + JSON API)
- Faults: Admin-specific error handling
"""

from .services import AdminService
from .controllers import AdminDashboardController
from .faults import (
    AdminAccessDeniedFault,
    BulkOperationFault,
    SystemHealthFault,
)

__all__ = [
    "AdminService",
    "AdminDashboardController",
    "AdminAccessDeniedFault", "BulkOperationFault", "SystemHealthFault",
]
