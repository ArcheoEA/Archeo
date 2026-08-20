import pytest

from ArcheoConverter.comparator import compare_models
from ArcheoConverter.models import ArchiMateModel, ArchiMateElement

def test_compare_models():
    m1 = ArchiMateModel(id="m1")
    m1.elements["e1"] = ArchiMateElement(id="e1", type="A", name="X")
    m2 = ArchiMateModel(id="m2")
    m2.elements["e1"] = ArchiMateElement(id="e1", type="A", name="Y")
    m2.elements["e2"] = ArchiMateElement(id="e2", type="B", name="Z")
    report = compare_models(m1, m2)
    assert "e2" in report.added_elements
    assert "e1" in report.modified_elements
