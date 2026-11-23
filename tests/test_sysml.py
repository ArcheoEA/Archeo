"""Tests for the SysML (XMI) parser."""

from __future__ import annotations

import pytest

from AcheoConverter.exceptions import ModelImportError
from AcheoConverter.formalisms.sysml.mapper import (
    DEFAULT_SYSML_ELEMENT_MAP,
    DEFAULT_SYSML_RELATIONSHIP_MAP,
)
from AcheoConverter.formalisms.sysml.parser import SysmlHandler
from AcheoConverter.formalisms.uml.parser import UmlHandler
from AcheoConverter.formalisms.registry import default_registry


@pytest.fixture()
def handler() -> SysmlHandler:
    return SysmlHandler()


def test_parse_sample_sysml(handler, sample_sysml):
    """The SysML sample parses into the expected structure."""
    parsed = handler.parse(sample_sysml, "sample_sysml.xmi")
    assert parsed.formalism == "sysml"
    assert parsed.version == "1.4"

    by_id = {e["id"]: e for e in parsed.elements}
    assert len(by_id) == 5
    assert by_id["bd1"]["type"] == "block-definition"
    assert by_id["pd1"]["type"] == "port-definition"
    assert by_id["cb1"]["type"] == "constraint-block"
    assert by_id["rb1"]["type"] == "requirement-block"

    # The package becomes the single folder containing everything.
    assert len(parsed.folders) == 1
    folder = parsed.folders[0]
    assert folder["name"] == "VehicleModel"
    assert set(folder["element_ids"]) == {"bd1", "bd2", "pd1", "cb1", "rb1"}

    rels = {r["id"]: r for r in parsed.relationships}
    assert len(rels) == 2
    assert rels["if1"]["type"] == "item-flow"
    assert (rels["if1"]["source"], rels["if1"]["target"]) == ("pd1", "bd2")
    assert rels["al1"]["type"] == "allocation"
    assert (rels["al1"]["source"], rels["al1"]["target"]) == ("bd1", "bd2")


def test_detection_sysml_not_captured_by_uml(handler, sample_sysml, sample_uml):
    """The SysML sample is not captured by the UML handler (and vice versa)."""
    assert handler.detect(sample_sysml, "x.xmi") == "1.4"
    assert UmlHandler().detect(sample_sysml, "x.xmi") is None
    assert SysmlHandler().detect(sample_uml, "x.xmi") is None


def test_registry_detection(sample_sysml):
    """The registry detects the SysML sample."""
    registry = default_registry()
    assert registry.detect(sample_sysml, "s.xmi") == ("sysml", "1.4")


def test_invalid_document_raises(handler):
    """Non-XMI documents raise ModelImportError."""
    with pytest.raises(ModelImportError):
        handler.parse(b"<model/>", "s.xmi")


def test_default_mapping_covers_sample(handler, sample_sysml):
    """Every SysML element/relationship type in the sample is mapped."""
    parsed = handler.parse(sample_sysml, "sample_sysml.xmi")
    for element in parsed.elements:
        assert element["type"] in DEFAULT_SYSML_ELEMENT_MAP, element["type"]
    for rel in parsed.relationships:
        assert rel["type"] in DEFAULT_SYSML_RELATIONSHIP_MAP, rel["type"]


def test_connector_with_owned_ends(handler):
    """Connector endpoints are resolved from owned-end parts."""
    xml = (
        b'<?xml version="1.0"?>'
        b'<xmi:XMI xmlns:xmi="http://www.omg.org/spec/XMI/20131001"'
        b' xmlns:sysml="http://www.eclipse.org/sysml/1.4">'
        b"<sysml:Package xmi:id=\"p\" name=\"P\">"
        b"<sysml:BlockDefinition xmi:id=\"b1\" name=\"B1\"/>"
        b"<sysml:BlockDefinition xmi:id=\"b2\" name=\"B2\"/>"
        b"<sysml:Connector xmi:id=\"c1\">"
        b"<sysml:ownedEnd xmi:id=\"e1\" part=\"b1\"/>"
        b"<sysml:ownedEnd xmi:id=\"e2\" part=\"b2\"/>"
        b"</sysml:Connector>"
        b"</sysml:Package>"
        b"</xmi:XMI>"
    )
    parsed = handler.parse(xml, "conn.xmi")
    assert len(parsed.relationships) == 1
    rel = parsed.relationships[0]
    assert rel["type"] == "connector"
    assert {rel["source"], rel["target"]} == {"b1", "b2"}
