import pytest

from ArcheoConverter.reporter import generate_model_summary
from ArcheoConverter.models import ArchiMateModel, ArchiMateElement

def test_summary():
    m = ArchiMateModel(id="m1", name="Test", version="3.2")
    m.elements["e1"] = ArchiMateElement(id="e1", type="BusinessProcess", name="P1")
    s = generate_model_summary(m)
    assert s["total_elements"] == 1
    assert s["version"] == "3.2"
