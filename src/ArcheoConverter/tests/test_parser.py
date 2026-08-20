import pytest

import tempfile
import os

from ArcheoConverter.parser import parse_archimate_stream

VALID_XML = """<?xml version="1.0"?>
<archimate xmlns="http://www.opengroup.org/xsd/archimate/3.2" version="3.2" id="m1" name="Test">
  <element id="e1" type="BusinessProcess" name="Proc1"/>
  <relationship id="r1" type="Association" source="e1" target="e2"/>
</archimate>"""

def test_parse_valid_xml():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
        f.write(VALID_XML)
        f.flush()
        model = parse_archimate_stream(f.name)
        os.unlink(f.name)
    assert model.version == "3.2"
    assert "e1" in model.elements
