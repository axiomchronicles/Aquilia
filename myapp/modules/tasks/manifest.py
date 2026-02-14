"""
Tasks Module - Manifest

Showcases fault domain configuration and recovery strategies.
"""

from aquilia import AppManifest
from aquilia.manifest import FaultHandlingConfig, FeatureConfig

manifest = AppManifest(
    name="tasks",
    version="0.1.0",
    description="Task management with structured faults, validation, and state machines",
    author="team@aquilia.dev",
    tags=["tasks", "faults", "effects"],

    services=[
        "modules.tasks.services:TaskService",
    ],
    controllers=[
        "modules.tasks.controllers:TasksController",
    ],

    route_prefix="/tasks",
    base_path="modules.tasks",

    faults=FaultHandlingConfig(
        default_domain="TASKS",
        strategy="propagate",
        handlers=[],
    ),

    features=[
        FeatureConfig(name="task_assignments", enabled=True),
        FeatureConfig(name="task_subtasks", enabled=False),
        FeatureConfig(name="task_time_tracking", enabled=False),
    ],
)
