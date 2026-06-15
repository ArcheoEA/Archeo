import pytest
from app.core.importer import ArchimateImporter

def test_successful_xml_import():
    # Mock Open Group XML content
    xml_data = b"""<?xml version="1.0" encoding="UTF-8"?>
    <exchange xmlns="http://www.opengroup.org/xsd/archimate/3.0/">
        <model name="Test Enterprise Architecture">
            <elements>
                <element identifier="id1" name="CEO" type="Stakeholder" />
                <element identifier="id2" name="Strategic Planning" type="BusinessProcess" />
                <element identifier="id3" name="ERP System" type="ApplicationComponent" />
            </elements>
            <relationships>
                <relationship identifier="rel1" type="Assignment" source="id1" target="id2" />
                <relationship identifier="rel2" type="Serving" source="id3" target="id2" />
            </relationships>
        </model>
    </exchange>
    """
    
    model_id = "test-import-123"
    model = ArchimateImporter.import_from_xml(xml_data, model_id)
    
    # Assertions
    assert model.name == "Test Enterprise Architecture"
    assert len(model.elements) == 3
    assert "id1" in model.elements
    assert model.elements["id1"].name == "CEO"
    assert len(model.relationships) == 2
    assert model.relationships[0].type == "Assignment"

def test_malformed_xml_import():
    xml_data = b"invalid xml content"
    with pytest.raises(ValueError, match="Malformed XML file"):
        ArchimateImporter.import_from_xml(xml_data, "fail-id")
