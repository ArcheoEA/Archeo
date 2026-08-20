import pytest

from ArcheoConverter.navigator import search_elements, filter_by_type
from ArcheoConverter.models import ArchiMateModel, ArchiMateElement

def test_search():
    m = ArchiMateModel(id="m1")
    m.elements["e1"] = ArchiMateElement(id="e1", type="A", name="Proc1")
    m.elements["e2"] = ArchiMateElement(id="e2", type="B", name="Proc2")
    assert len(search_elements(m, "Proc")) == 2
    assert filter_by_type(m, "A") == ["e1"]
