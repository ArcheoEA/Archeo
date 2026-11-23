"""Tests for the BPMN 2.0 parser and its default ArchiMate mapping."""

from __future__ import annotations

import pytest

from ArcheoConverter.exceptions import ModelImportError
from ArcheoConverter.formalisms.bpmn.mapper import (
    DEFAULT_BPMN_ELEMENT_MAP,
    DEFAULT_BPMN_RELATIONSHIP_MAP,
)
from ArcheoConverter.formalisms.bpmn.parser import BpmnHandler
from ArcheoConverter.formalisms.registry import default_registry


@pytest.fixture()
def handler() -> BpmnHandler:
    return BpmnHandler()


def test_parse_sample_bpmn(handler, sample_bpmn):
    """The BPMN sample parses into the expected BPMN-native structure."""
    parsed = handler.parse(sample_bpmn, "sample.bpmn")
    assert parsed.formalism == "bpmn"
    assert parsed.version == "2.0"
    by_id = {e["id"]: e for e in parsed.elements}

    # 8 elements inside the process folder.
    process_folder = by_id["proc1"]["folder_id"]
    assert by_id["proc1"]["type"] == "process"
    in_process = [e for e in parsed.elements if e["folder_id"] == process_folder]
    assert len(in_process) == 8
    assert by_id["t1"]["type"] == "task"
    assert by_id["t2"]["type"] == "user-task"
    assert by_id["t3"]["type"] == "service-task"
    assert by_id["g1"]["type"] == "exclusive-gateway"
    assert by_id["se1"]["type"] == "start-event"
    assert by_id["ee1"]["type"] == "end-event"

    # Participant in the Participants folder; data objects in General.
    assert by_id["p1"]["type"] == "participant"
    general = next(f for f in parsed.folders if f["name"] == "General")
    general_ids = set(general["element_ids"])
    assert {"do1", "ds1", "m1"} <= general_ids
    assert by_id["do1"]["type"] == "data-object"
    assert by_id["ds1"]["type"] == "data-store"
    assert by_id["m1"]["type"] == "message"

    # Flows.
    rels = {r["id"]: r for r in parsed.relationships}
    assert len(rels) == 7
    assert rels["f1"]["type"] == "sequence-flow"
    assert rels["f1"]["source"] == "se1"
    assert rels["f1"]["target"] == "t1"
    assert rels["mf1"]["type"] == "message-flow"
    assert rels["mf1"]["source"] == "t3"
    assert rels["mf1"]["target"] == "p1"

    # Folders: process + participants + general.
    folder_names = {f["name"] for f in parsed.folders}
    assert {"Order Processing", "Participants", "General"} == folder_names


def test_detection(handler, sample_bpmn, sample_32):
    """detect() recognizes BPMN and rejects other formats."""
    assert handler.detect(sample_bpmn, "x.bpmn") == "2.0"
    assert handler.detect(sample_32, "x.archimate") is None


def test_registry_detection(sample_bpmn):
    """The registry detects the BPMN sample."""
    registry = default_registry()
    assert registry.detect(sample_bpmn, "b.bpmn") == ("bpmn", "2.0")


def test_invalid_document_raises(handler):
    """Non-BPMN roots raise ModelImportError."""
    with pytest.raises(ModelImportError):
        handler.parse(b"<model/>", "x.bpmn")
    with pytest.raises(ModelImportError):
        handler.parse(b"not xml", "x.bpmn")


def test_default_mapping_covers_all_parsed_types(handler, sample_bpmn):
    """Every BPMN element/relationship type has a default ArchiMate mapping."""
    parsed = handler.parse(sample_bpmn, "sample.bpmn")
    for element in parsed.elements:
        assert element["type"] in DEFAULT_BPMN_ELEMENT_MAP, element["type"]
    for rel in parsed.relationships:
        assert rel["type"] in DEFAULT_BPMN_RELATIONSHIP_MAP, rel["type"]


def test_skipped_references_reported(handler):
    """dataObjectReference & co are skipped and reported."""
    xml = (
        b'<?xml version="1.0"?>'
        b'<definitions xmlns="http://www.omg.org/spec/BPMN/20100524/MODEL">'
        b'<dataObject id="d1" name="D"/>'
        b'<dataObjectReference id="dr1" dataObjectRef="d1"/>'
        b"<process id=\"p\" name=\"P\">"
        b"<task id=\"t\" name=\"T\"/>"
        b"</process>"
        b"</definitions>"
    )
    parsed = handler.parse(xml, "refs.bpmn")
    assert any("dataObjectReference" in s for s in parsed.skipped)
    # The referenced data object itself is still imported.
    assert {e["id"] for e in parsed.elements} >= {"d1", "p", "t"}
