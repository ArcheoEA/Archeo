import pytest

from ArcheoConverter.converter import migrate_model
from ArcheoConverter.models import ArchiMateModel, ArchiMateElement

def test_migration_32_to_40():
    m = ArchiMateModel(id="m1", version="3.2")
    m.elements["e1"] = ArchiMateElement(id="e1", type="BusinessObject", name="Obj1")
    new_m = migrate_model(m, "4.0")
    assert new_m.version == "4.0"
    assert new_m.elements["e1"].type == "DataObject"
