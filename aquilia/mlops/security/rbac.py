"""
RBAC for registry operations.

Defines roles and permissions for modelpack management.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("aquilia.mlops.security.rbac")


class Permission(str, Enum):
    """Registry permissions."""
    PACK_READ = "pack:read"
    PACK_WRITE = "pack:write"
    PACK_DELETE = "pack:delete"
    PACK_PROMOTE = "pack:promote"
    PACK_SIGN = "pack:sign"
    REGISTRY_ADMIN = "registry:admin"
    PLUGIN_INSTALL = "plugin:install"
    ROLLOUT_MANAGE = "rollout:manage"


@dataclass
class Role:
    """A named role with a set of permissions."""
    name: str
    permissions: Set[Permission] = field(default_factory=set)
    description: str = ""


# Built-in roles
VIEWER = Role(
    name="viewer",
    permissions={Permission.PACK_READ},
    description="Read-only access to modelpacks",
)

DEVELOPER = Role(
    name="developer",
    permissions={
        Permission.PACK_READ,
        Permission.PACK_WRITE,
        Permission.PACK_SIGN,
    },
    description="Read/write access to modelpacks",
)

DEPLOYER = Role(
    name="deployer",
    permissions={
        Permission.PACK_READ,
        Permission.PACK_PROMOTE,
        Permission.ROLLOUT_MANAGE,
    },
    description="Deploy and manage rollouts",
)

ADMIN = Role(
    name="admin",
    permissions=set(Permission),
    description="Full registry administration",
)

BUILTIN_ROLES = {r.name: r for r in [VIEWER, DEVELOPER, DEPLOYER, ADMIN]}


class RBACManager:
    """
    Role-based access control for registry operations.
    """

    def __init__(self):
        self._user_roles: Dict[str, Set[str]] = {}  # user_id → role names
        self._roles = dict(BUILTIN_ROLES)

    def assign_role(self, user_id: str, role_name: str) -> None:
        if role_name not in self._roles:
            raise ValueError(f"Unknown role: {role_name}")
        self._user_roles.setdefault(user_id, set()).add(role_name)

    def revoke_role(self, user_id: str, role_name: str) -> None:
        roles = self._user_roles.get(user_id, set())
        roles.discard(role_name)

    def check_permission(self, user_id: str, permission: Permission) -> bool:
        roles = self._user_roles.get(user_id, set())
        for role_name in roles:
            role = self._roles.get(role_name)
            if role and permission in role.permissions:
                return True
        return False

    def get_user_permissions(self, user_id: str) -> Set[Permission]:
        perms: Set[Permission] = set()
        for role_name in self._user_roles.get(user_id, set()):
            role = self._roles.get(role_name)
            if role:
                perms.update(role.permissions)
        return perms

    def add_role(self, role: Role) -> None:
        self._roles[role.name] = role
