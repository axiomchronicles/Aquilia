"""
Test 17: Flow System (flow.py)

Tests FlowNode, FlowNodeType.
"""

import pytest
from aquilia.flow import FlowNode, FlowNodeType


# ============================================================================
# FlowNodeType
# ============================================================================

class TestFlowNodeType:

    def test_values(self):
        assert FlowNodeType.GUARD == "guard"
        assert FlowNodeType.TRANSFORM == "transform"
        assert FlowNodeType.HANDLER == "handler"
        assert FlowNodeType.HOOK == "hook"

    def test_is_string_enum(self):
        assert isinstance(FlowNodeType.GUARD, str)
        assert isinstance(FlowNodeType.HANDLER, str)


# ============================================================================
# FlowNode
# ============================================================================

class TestFlowNode:

    def test_create(self):
        def my_handler(req):
            return "ok"

        node = FlowNode(
            type=FlowNodeType.HANDLER,
            callable=my_handler,
            name="my_handler",
        )
        assert node.type == FlowNodeType.HANDLER
        assert node.name == "my_handler"
        assert node.priority == 50
        assert node.effects == []

    def test_guard_node(self):
        def my_guard(req):
            return True

        node = FlowNode(
            type=FlowNodeType.GUARD,
            callable=my_guard,
            name="auth_guard",
            priority=10,
        )
        assert node.type == FlowNodeType.GUARD
        assert node.priority == 10

    def test_transform_node(self):
        def transform(data):
            return data

        node = FlowNode(
            type=FlowNodeType.TRANSFORM,
            callable=transform,
            name="json_transform",
        )
        assert node.type == FlowNodeType.TRANSFORM

    def test_hook_node(self):
        def hook():
            pass

        node = FlowNode(
            type=FlowNodeType.HOOK,
            callable=hook,
            name="after_hook",
        )
        assert node.type == FlowNodeType.HOOK

    def test_with_effects(self):
        def handler(req):
            return "ok"

        node = FlowNode(
            type=FlowNodeType.HANDLER,
            callable=handler,
            name="db_handler",
            effects=["db", "cache"],
        )
        assert "db" in node.effects
        assert "cache" in node.effects

    def test_callable_stored(self):
        def my_fn():
            return 42

        node = FlowNode(
            type=FlowNodeType.HANDLER,
            callable=my_fn,
            name="test",
        )
        assert node.callable() == 42
