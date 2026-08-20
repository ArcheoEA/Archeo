# tests/test_element.py

"""
Tests for core element classes.
"""

import pytest
from pydantic import ValidationError

from ArcheoConverter.core.element import (
    ArchiElement_v32,
    ArchiElement_v40,
    ElementTypes_v32,
    ElementTypes_v40,
)


def test_archielement_v32_creation():
    """Test creating an ArchiElement v3.2."""
    elem = ArchiElement_v32(
        name="Business Actor",
        type=ElementTypes_v32.BusinessActor
    )
    
    assert elem.id is not None
    assert elem.name == "Business Actor"
    assert isinstance(elem.type, ElementTypes_v32)
    assert elem.description is None


def test_archielement_v40_creation():
    """Test creating an ArchiElement v4.0."""
    elem = ArchiElement_v40(
        name="Goal",
        type=ElementTypes_v40.Goal,
        is_abstract=True
    )
    
    assert elem.is_abstract is True
    assert isinstance(elem, ArchiElement_v40)


def test_archielement_v32_validation():
    """Test validation of v3.2 element."""
    with pytest.raises(ValidationError):
        # Missing required 'name' field
        ArchiElement_v32(type=ElementTypes_v32.BusinessActor)
    
    with pytest.raises(ValidationError):
        # Invalid type (not ElementTypes_v32)
        ArchiElement_v32(name="Test", type="invalid_type")


def test_archielement_v40_inheritance():
    """Test that v4.0 element inherits from v3.2."""
    elem = ArchiElement_v40(
        name="Test",
        type=ElementTypes_v40.BusinessActor
    )
    
    # Should have all v3.2 attributes
    assert hasattr(elem, "name")
    assert hasattr(elem, "type")
    assert hasattr(elem, "folder_id")
