"""
CRM Tasks Module Manifest
===========================

Provides task management with priorities, due dates,
status tracking, assignment, and overdue detection.
"""

from aquilia.manifest import AppManifest, FaultHandlingConfig


manifest = AppManifest(
    name="tasks",
    version="1.0.0",
    description="CRM task management module",
    services=[
        "modules.tasks.services:TaskService",
    ],
    controllers=[
        "modules.tasks.controllers:TaskController",
        "modules.tasks.controllers:TaskAPIController",
    ],
    route_prefix="/tasks",
    base_path="modules.tasks",
    faults=FaultHandlingConfig(
        default_domain="TASKS",
        strategy="propagate",
    ),
    depends_on=["crm_auth"],
    tags=["tasks", "crm"],
)
