import pytest

import tempfile
import os

from ArcheoConverter.exporter import export_to_xml
from ArcheoConverter.models import ArchiMateModel, ArchiMateElement

def test_export():
    m = ArchiMateModel(id="m1", name="Test", version="3.2")
    m.elements["e1"] = ArchiMateElement(id="e1", type="BusinessProcess", name="P1")
    with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as f:
        export_to_xml(m, f.name)
        assert os.path.exists(f.name)
        with open(f.name) as rf:
            assert "BusinessProcess" in rf.read()
        os.unlink(f.name)
