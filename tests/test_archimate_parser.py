"""Tests for the ArchiMate Model Exchange parser (3.2 / 4.0)."""

from __future__ import annotations

import pytest

from ArcheoConverter.exceptions import ModelImportError, UnsupportedFormalismError
from ArcheoConverter.formalisms.archimate.parser import ArchiMateHandler
from ArcheoConverter.formalisms.registry import default_registry


@pytest.fixture()
def handler() -> ArchiMateHandler:
    return ArchiMateHandler()


def test_parse_sample_32(handler, sample_32):
    """The 3.2 sample parses with the expected structure."""
    parsed = handler.parse(sample_32, "sample_32.archimate")
    assert parsed.formalism == "archimate"
    assert parsed.version == "3.2"
    assert len(parsed.elements) == 14
    assert len(parsed.relationships) == 9
    assert len(parsed.folders) == 4

    by_id = {e["id"]: e for e in parsed.elements}
    assert by_id["ba1"]["type"] == "business-actor"
    assert by_id["ba1"]["stereotypes"] == ["External"]
    assert by_id["ba1"]["properties"]["__tags"] == ["customer"]
    assert by_id["bs1"]["properties"]["owner"] == "Sales"
    assert by_id["g1"]["description"].startswith("Reduce the cost")
    assert by_id["ba1"]["folder_id"] is not None

    rels = {r["id"]: r for r in parsed.relationships}
    assert rels["r1"]["type"] == "serving"
    assert rels["r6"]["type"] == "aggregation"
    assert rels["r6"]["aggregation"] is True
    # <aggregation aggregation="false"/> is an Association.
    assert rels["r7"]["type"] == "association"
    assert rels["r7"]["aggregation"] is False
    assert rels["r9"]["type"] == "association"


def test_parse_sample_40_detects_version(handler, sample_40):
    """A file containing 4.0-only concepts is detected as 4.0."""
    parsed = handler.parse(sample_40, "sample_40.archimate")
    assert parsed.version == "4.0"
    by_id = {e["id"]: e for e in parsed.elements}
    assert by_id["res1"]["type"] == "resource"
    assert by_id["res1"]["stereotypes"] == ["storage"]
    assert len(parsed.elements) == 12
    assert len(parsed.relationships) == 7


def test_explicit_version_wins(handler, sample_32):
    """An explicit version override is honored."""
    parsed = handler.parse(sample_32, "s.archimate", version="4.0")
    assert parsed.version == "4.0"


def test_detection(handler, sample_32, sample_40, sample_bpmn, sample_uml):
    """detect() recognizes ArchiMate (3.2/4.0) and rejects other formalisms."""
    assert handler.detect(sample_32, "x") == "3.2"
    assert handler.detect(sample_40, "x") == "4.0"
    assert handler.detect(sample_bpmn, "x.bpmn") is None
    assert handler.detect(sample_uml, "x.xmi") is None


def test_registry_detects_each_formalism(sample_32, sample_40, sample_bpmn, sample_uml, sample_sysml):
    """The registry auto-detects each sample's formalism."""
    registry = default_registry()
    assert registry.detect(sample_32, "a") == ("archimate", "3.2")
    assert registry.detect(sample_40, "a") == ("archimate", "4.0")
    assert registry.detect(sample_bpmn, "b") == ("bpmn", "2.0")
    assert registry.detect(sample_uml, "c") == ("uml", "2.5")
    assert registry.detect(sample_sysml, "d") == ("sysml", "1.4")


def test_invalid_xml_raises(handler):
    """Malformed XML raises ModelImportError."""
    with pytest.raises(ModelImportError):
        handler.parse(b"<model><broken", "bad.xml")


def test_wrong_root_raises(handler):
    """A non-model root raises ModelImportError."""
    with pytest.raises(ModelImportError):
        handler.parse(b"<other/>", "wrong.xml")


def test_unknown_element_tag_kept_as_extension(handler):
    """Unknown element tags are preserved as 'extension' with a warning."""
    xml = (
        b'<model xmlns="http://example.com/ns">'
        b"<folder name=\"F\" type=\"other\">"
        b"<futureThing name=\"Fut\" id=\"e1\"/>"
        b"</folder></model>"
    )
    parsed = handler.parse(xml, "future.archimate")
    assert parsed.elements[0]["type"] == "extension"
    assert parsed.elements[0]["properties"]["__source_tag"] == "futureThing"
    assert any("futureThing" in w for w in parsed.warnings)


def test_unknown_relationship_tag_kept(handler):
    """Unknown relationship tags (with endpoints) are kept with a warning."""
    xml = (
        b'<model xmlns="http://example.com/ns">'
        b"<folder name=\"F\" type=\"other\">"
        b"<node name=\"N1\" id=\"a\"/>"
        b"<node name=\"N2\" id=\"b\"/>"
        b"</folder>"
        b"<futureRelation id=\"r1\" source=\"a\" target=\"b\"/>"
        b"</model>"
    )
    parsed = handler.parse(xml, "rel.archimate")
    assert parsed.relationships[0]["type"] == "future-relation"
    assert any("futureRelation" in w for w in parsed.warnings)


def test_missing_ids_are_generated(handler):
    """Elements/relationships without ids get generated ones (warning)."""
    xml = (
        b'<model xmlns="http://example.com/ns">'
        b"<folder name=\"F\" type=\"other\">"
        b"<node name=\"N1\"/>"
        b"</folder>"
        b"</model>"
    )
    parsed = handler.parse(xml, "noid.archimate")
    assert parsed.elements[0]["id"].startswith("elem-")
    assert any("no id" in w for w in parsed.warnings)


def test_detect_version_of_40_sample(handler, sample_40):
    """detect() reports 4.0 for the 4.0 sample."""
    assert handler.detect(sample_40, "x") == "4.0"


def test_empty_model_parses(handler):
    """An empty <model> parses (zero entities)."""
    parsed = handler.parse(b"<model/>", "empty.archimate")
    assert parsed.elements == []
    assert parsed.relationships == []
    assert parsed.folders == []
