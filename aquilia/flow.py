"""
Aquilia Flow - Pipeline System
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, List, Optional

class FlowNodeType(str, Enum):
    GUARD = "guard"
    TRANSFORM = "transform"
    HANDLER = "handler"
    HOOK = "hook"

@dataclass
class FlowNode:
    type: FlowNodeType
    callable: Callable[..., Any]
    name: str
    priority: int = 50
    effects: List[str] = field(default_factory=list)
