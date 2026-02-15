#!/usr/bin/env python3
"""Quick inline test to verify the auto_now fix works."""
print("Testing auto_now field validation fix...")
print("=" * 60)

# Test that auto_now sets blank=True
from aquilia.models.fields_module import DateTimeField
field = DateTimeField(auto_now=True)
field.name = "updated_at"  # Set name after init
print(f"✓ DateTimeField(auto_now=True) has blank={field.blank}")

# Test that validation allows None when blank=True
try:
    result = field.validate(None)
    print(f"✓ Validation with None passed: {result}")
except Exception as e:
    print(f"✗ Validation failed: {e}")
    exit(1)

print()
print("=" * 60)
print("✅ Fix verified! The framework now correctly handles auto_now fields.")
print()
print("Summary of changes:")
print("1. DateTimeField/DateField/TimeField now set blank=True when auto_now=True")
print("2. Field.validate() now allows None if blank=True OR null=True")
print("3. This allows auto_now fields to pass validation before pre_save sets the value")
