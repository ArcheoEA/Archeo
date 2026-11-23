"""Tests for the UML (XMI) parser and the shared XMI walker."""

from __future__ import annotations

import pytest

from AcheoConverter.exceptions import ModelImportError
from AcheoConverter.formalisms.uml.mapper import (
    DEFAULT_UML_ELEMENT_MAP,
    DEFAULT_UML_RELATIONSHIP_MAP,
)
from AcheoConverter.formalisms.uml.parser import UmlHandler
from AcheoConverter.formalisms.xmi import parse_xmi


@pytest.fixture()
def handler() -> UmlHandler:
    return UmlHandler()


def test_parse_sample_uml(handler, sample_uml):
    """The UML sample parses into the expected structure."""
    parsed = handler.parse(sample_uml, "sample_uml.xmi")
    assert parsed.formalism == "uml"
    assert parsed.version == "2.5"

    by_id = {e["id"]: e for e in parsed.elements}
    assert len(by_id) == 7
    assert by_id["c1"]["type"] == "class"
    assert by_id["i1"]["type"] == "interface"
    assert by_id["act1"]["type"] == "activity"
    assert by_id["ac1"]["type"] == "action"  # lowercase tag normalized
    assert by_id["st1"]["type"] == "state"

    # Packages become folders (Model is the root folder).
    folders = {f["id"]: f for f in parsed.folders}
    assert len(folders) == 3
    assert by_id["c1"]["folder_id"] == "pkg1"
    assert by_id["act1"]["folder_id"] == "pkg2"
    assert folders["pkg1"]["parent_id"] == "m1"
    assert folders["m1"]["parent_id"] is None

    # Relationships resolved from connectors.
    rels = {r["id"]: r for r in parsed.relationships}
    assert len(rels) == 3
    assert rels["a1"]["type"] == "association"
    assert {rels["a1"]["source"], rels["a1"]["target"]} == {"c1", "c2"}
    assert rels["r1"]["type"] == "realization"
    assert (rels["r1"]["source"], rels["r1"]["target"]) == ("c1", "i1")
    assert rels["of1"]["type"] == "object-flow"
    assert (rels["of1"]["source"], rels["of1"]["target"]) == ("ac1", "ac2")


def test_detection(handler, sample_uml, sample_sysml, sample_bpmn):
    """detect() recognizes UML and rejects SysML / BPMN."""
    assert handler.detect(sample_uml, "x.xmi") == "2.5"
    # SysML shares UseCase/StateMachine types but carries its own namespace.
    assert handler.detect(sample_sysml, "x.xmi") is None
    assert handler.detect(sample_bpmn, "x.bpmn") is None


def test_invalid_xmi_raises(handler):
    """Non-XMI documents raise ModelImportError."""
    with pytest.raises(ModelImportError):
        handler.parse(b"<definitions/>", "x.xmi")
    with pytest.raises(ModelImportError):
        handler.parse(b"junk", "x.xmi")


def test_default_mapping_covers_sample(handler, sample_uml):
    """Every UML element/relationship type in the sample is mapped."""
    parsed = handler.parse(sample_uml, "sample_uml.xmi")
    for element in parsed.elements:
        assert element["type"] in DEFAULT_UML_ELEMENT_MAP, element["type"]
    for rel in parsed.relationships:
        assert rel["type"] in DEFAULT_UML_RELATIONSHIP_MAP, rel["type"]


def test_xmi_walker_collects_nodes_and_refs(sample_uml):
    """The shared walker returns nodes with resolved single references."""
    nodes, warnings = parse_xmi(sample_uml, context="test")
    by_id = {n.node_id: n for n in nodes}
    assert "m1" in by_id and "c1" in by_id and "ae1" in by_id
    realization = by_id["r1"]
    assert realization.single_refs.get("client") == "c1"
    assert realization.single_refs.get("supplier") == "i1"
    owned_end = by_id["ae1"]
    assert owned_end.single_refs.get("type") == "c1"
    assert owned_end.parent_id == "a1"
    assert warnings == []


def test_xmi_walker_type_name_from_xmi_type(sample_uml):
    """The xmi:type attribute (qualified) wins over the tag local name."""
    nodes, _ = parse_xmi(sample_uml, context="test")
    by_id = {n.node_id: n for n in nodes}
    assert by_id["c1"].type_name == "Class"
    assert by_id["ac1"].type_name == "action" or by_id["ac1"].type_name == "Action"
