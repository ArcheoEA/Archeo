import pytest

from ArcheoConverter.models import ArchiMateModel, ArchiMateElement, ArchiMateRelationship, ArchiMateView

def test_model_creation():
    m = ArchiMateModel(id="test-1", name="Test", version="3.2")
    assert m.id == "test-1"
    assert m.version == "3.2"

def test_element_addition():
    m = ArchiMateModel(id="m1")
    m.elements["e1"] = ArchiMateElement(id="e1", type="BusinessProcess", name="Proc1")
    assert "e1" in m.elements
    assert m.elements["e1"].type == "BusinessProcess"
