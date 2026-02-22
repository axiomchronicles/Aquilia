import pytest
from aquilia.models.fields import SmallAutoField, VarcharField, FieldValidationError

def test_small_auto_field():
    # Test instantiation
    field = SmallAutoField(primary_key=True)
    assert field.primary_key is True
    assert field._field_type == "SMALLAUTO"
    
    # Test sql type inference
    assert field.sql_type("sqlite") == "INTEGER"
    assert "SMALLSERIAL" in field.sql_type("postgresql").upper()
    
    # Test validation
    assert field.validate(None) is None
    assert field.validate(150) == 150
    assert field.validate("150") == 150
    
    with pytest.raises(FieldValidationError):
        field.validate(50000) # Out of 16-bit range
        
    with pytest.raises(FieldValidationError):
        field.validate("invalid_int")

def test_varchar_field():
    # Test instantiation and inheritance
    field = VarcharField(max_length=200)
    assert field.max_length == 200
    assert field._field_type == "VARCHAR"
    
    # Test sql type inference
    assert field.sql_type() == "VARCHAR(200)"
    
    # Test validation (inherited from CharField)
    assert field.validate("test") == "test"
    
    with pytest.raises(FieldValidationError):
        field.validate("a" * 201) # Exceeds max length
