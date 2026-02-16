#!/usr/bin/env python3.14
"""
Quick Demo: DI-Serializer Integration

Run this to see the new features in action.
"""

import asyncio
from aquilia.serializers import Serializer, CharField, IntegerField, HiddenField
from aquilia.serializers.fields import (
    CurrentUserDefault,
    CurrentRequestDefault,
    InjectDefault,
)
from aquilia.serializers.validators import RangeValidator, CompoundValidator, MinLengthValidator


# ============================================================================
# Demo: DI-Aware Defaults
# ============================================================================

class FakeIdentity:
    """Mock identity for demo."""
    def __init__(self, id=42, username="demo_user"):
        self.id = id
        self.username = username


class FakeRequest:
    """Mock request for demo."""
    def __init__(self, identity=None, client_ip="127.0.0.1"):
        self.client_ip = client_ip
        self.method = "POST"
        self.state = {}
        if identity:
            self.state["identity"] = identity


class DemoArticleSerializer(Serializer):
    """Demo serializer with all the new features."""
    
    title = CharField(
        max_length=200,
        validators=[
            CompoundValidator(
                MinLengthValidator(3),
                mode="and",
            )
        ]
    )
    
    content = CharField(
        validators=[MinLengthValidator(10)]
    )
    
    # DI-aware defaults
    author_id = HiddenField(default=CurrentUserDefault())
    client_ip = HiddenField(default=CurrentRequestDefault(attr="client_ip"))
    view_count = IntegerField(
        default=0,
        validators=[RangeValidator(0, 1000000)]
    )


def demo_di_defaults():
    """Demonstrate DI-aware defaults in action."""
    print("=" * 70)
    print("DEMO: DI-Aware Defaults")
    print("=" * 70)
    
    # Create mock context
    identity = FakeIdentity(id=42, username="kai")
    request = FakeRequest(identity=identity, client_ip="192.168.1.100")
    
    # User provides only title and content
    user_data = {
        "title": "My Article",
        "content": "This is the article content that is long enough...",
    }
    
    print(f"\n📥 Input data from user:")
    print(f"   {user_data}")
    
    # Create serializer with DI context
    serializer = DemoArticleSerializer(
        data=user_data,
        context={
            "request": request,
            "identity": identity,
        }
    )
    
    # Validate
    if serializer.is_valid():
        print(f"\n✅ Validation passed!")
        print(f"\n📤 Validated data (with DI-injected defaults):")
        for key, value in serializer.validated_data.items():
            marker = "🔒" if key in ["author_id", "client_ip"] else "📝"
            injected = " (auto-injected)" if key in ["author_id", "client_ip", "view_count"] else ""
            print(f"   {marker} {key}: {value}{injected}")
    else:
        print(f"\n❌ Validation failed:")
        for field, errors in serializer.errors.items():
            print(f"   - {field}: {errors}")


def demo_validation_failures():
    """Demonstrate validation errors."""
    print("\n" + "=" * 70)
    print("DEMO: Validation Failures")
    print("=" * 70)
    
    identity = FakeIdentity(id=99)
    request = FakeRequest(identity=identity)
    
    # Invalid data (title too short, content missing)
    invalid_data = {
        "title": "AB",  # Too short (< 3 chars)
        "content": "Short",  # Too short (< 10 chars)
    }
    
    print(f"\n📥 Invalid input data:")
    print(f"   {invalid_data}")
    
    serializer = DemoArticleSerializer(
        data=invalid_data,
        context={"request": request, "identity": identity}
    )
    
    if not serializer.is_valid():
        print(f"\n❌ Validation failed (as expected):")
        for field, errors in serializer.errors.items():
            print(f"   - {field}: {errors}")


def demo_range_validator():
    """Demonstrate RangeValidator."""
    print("\n" + "=" * 70)
    print("DEMO: RangeValidator")
    print("=" * 70)
    
    identity = FakeIdentity(id=10)
    request = FakeRequest(identity=identity)
    
    print("\n📝 Testing view_count with RangeValidator(0, 1000000)...")
    
    # Valid range
    valid_data = {
        "title": "Valid Article",
        "content": "Content is long enough for validation...",
        "view_count": 500,
    }
    
    s1 = DemoArticleSerializer(data=valid_data, context={"request": request, "identity": identity})
    print(f"\n   ✅ view_count=500: {'PASS' if s1.is_valid() else 'FAIL'}")
    
    # Out of range
    invalid_data = {
        "title": "Invalid Article",
        "content": "Content is long enough for validation...",
        "view_count": 2_000_000,  # Too high
    }
    
    s2 = DemoArticleSerializer(data=invalid_data, context={"request": request, "identity": identity})
    if not s2.is_valid():
        print(f"   ❌ view_count=2000000: FAIL (out of range)")
        print(f"      Error: {s2.errors.get('view_count')}")


def demo_context_access():
    """Demonstrate accessing DI container and request from serializer."""
    print("\n" + "=" * 70)
    print("DEMO: Context Access in Serializer")
    print("=" * 70)
    
    identity = FakeIdentity(id=77, username="context_demo")
    request = FakeRequest(identity=identity, client_ip="10.0.0.1")
    
    # Create a custom serializer that uses context
    class ContextAwareSerializer(Serializer):
        title = CharField()
        author_id = HiddenField(default=CurrentUserDefault())
        
        def validate(self, attrs):
            """Custom validation using request from context."""
            # Access request from serializer
            if self.request:
                print(f"\n   📍 Inside validate(): request.client_ip = {self.request.client_ip}")
                print(f"   📍 Inside validate(): request.method = {self.request.method}")
            
            # Access identity from context
            identity = self.context.get("identity")
            if identity:
                print(f"   📍 Inside validate(): identity.username = {identity.username}")
            
            return attrs
    
    data = {"title": "Context Test"}
    serializer = ContextAwareSerializer(
        data=data,
        context={"request": request, "identity": identity}
    )
    
    print(f"\n📥 Validating: {data}")
    if serializer.is_valid():
        print(f"\n✅ Validation passed")
        print(f"   Result: {serializer.validated_data}")


# ============================================================================
# Main
# ============================================================================

def main():
    """Run all demos."""
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 68 + "║")
    print("║" + "   Aquilia DI-Serializer Integration Demo".center(68) + "║")
    print("║" + " " * 68 + "║")
    print("╚" + "═" * 68 + "╝")
    
    demo_di_defaults()
    demo_validation_failures()
    demo_range_validator()
    demo_context_access()
    
    print("\n" + "=" * 70)
    print("✨ Demo Complete!")
    print("=" * 70)
    print("\nKey Features Demonstrated:")
    print("  ✓ CurrentUserDefault - Auto-inject user ID")
    print("  ✓ CurrentRequestDefault - Auto-inject request attributes")
    print("  ✓ RangeValidator - Combined min/max validation")
    print("  ✓ CompoundValidator - Multiple validators with AND logic")
    print("  ✓ Context access - Use self.request and self.container")
    print("\nFor more examples, see:")
    print("  - myapp/modules/blogs/serializers.py")
    print("  - myapp/modules/blogs/controllers.py")
    print("  - myapp/modules/blogs/examples_advanced.py")
    print("  - myapp/modules/blogs/README.md")
    print()


if __name__ == "__main__":
    main()
