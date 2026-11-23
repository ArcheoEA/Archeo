"""Tests for the ArchiMate Model Exchange exporter (round-trips included)."""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest

from ArcheoConverter.core.repository import ModelRepository
from ArcheoConverter.exceptions import ExportError
from ArcheoConverter.formalisms.archimate.exporter import (
    ArchiMateExporter,
    ExportSelection,
    folder_has_content,
)
from ArcheoConverter.formalisms.registry import default_registry
from ArcheoConverter.services.importer import ImportService


@pytest.fixture()
def importer() -> ImportService:
    return ImportService(default_registry(), max_upload_bytes=10 * 1024 * 1024)


@pytest.fixture()
def model_32(importer, sample_32):
    """The 3.2 sample as a canonical in-memory model."""
    repo = ModelRepository()
    result = importer.import_content(sample_32, repository=repo,
                                     filename="s32.archimate", model_id="m32")
    return repo.get(result.model_id)


@pytest.fixture()
def model_40(importer, sample_40):
    """The 4.0 sample as a canonical in-memory model."""
    repo = ModelRepository()
    result = importer.import_content(sample_40, repository=repo,
                                     filename="s40.archimate", model_id="m40")
    return repo.get(result.model_id)


def _local(tag) -> str:
    return tag.rsplit("}", 1)[-1] if isinstance(tag, str) else ""


def test_export_roundtrip_32(model_32, importer):
    """Exporting and re-importing a 3.2 model preserves its content."""
    exporter = ArchiMateExporter()
    result = exporter.export(model_32, version="3.2")
    assert result.version == "3.2"
    assert result.element_count == 14
    assert result.relationship_count == 9
    assert result.folder_count == 4

    repo = ModelRepository()
    importer.import_content(result.xml, repository=repo,
                            filename="roundtrip.archimate", model_id="rt")
    model = repo.get("rt")
    assert len(model.elements) == 14
    assert len(model.relationships) == 9
    assert len(model.folders) == 4
    # Spot-check that a stereotype, a property and the aggregation
    # convention (true -> aggregation, false -> association) survived.
    assert model.elements["ba1"].stereotypes == ["External"]
    assert model.elements["bs1"].properties["owner"] == "Sales"
    assert model.relationships["r6"].type == "aggregation"
    assert model.relationships["r7"].type == "association"


def test_export_declares_exchange_namespace(model_32):
    """The exported document uses the Model Exchange namespace + XML header."""
    result = ArchiMateExporter().export(model_32, version="3.2")
    root = ET.fromstring(result.xml)
    assert _local(root.tag) == "model"
    assert root.tag.startswith("{http://www.archimatetool.org/archimate/types}")
    text = result.xml.decode("utf-8")
    assert text.startswith("<?xml")
    assert "businessActor" in text


def test_export_40_only_concept_becomes_extension_without_conversion(model_40):
    """Direct export (no conversion) of a 4.0-only concept emits 'extension'.

    The version *mapping* (resource -> technology-resource) is the job of
    the conversion engine; the exporter alone only guarantees a well-formed
    3.2 document.
    """
    result = ArchiMateExporter().export(model_40, version="3.2")
    root = ET.fromstring(result.xml)
    tags = {_local(el.tag) for el in root.iter()}
    assert "resource" not in tags
    assert "extension" in tags
    assert any("unknown in ArchiMate 3.2" in w for w in result.warnings)


def test_export_40_keeps_resource_tag(model_40):
    """Exporting to 4.0 keeps the 4.0-only 'resource' tag."""
    result = ArchiMateExporter().export(model_40, version="4.0")
    root = ET.fromstring(result.xml)
    tags = {_local(el.tag) for el in root.iter()}
    assert "resource" in tags


def test_export_partial_selection(model_32):
    """Partial selection exports only the chosen elements/relationships."""
    exporter = ArchiMateExporter()
    result = exporter.export(
        model_32,
        version="3.2",
        selection=ExportSelection(element_ids={"ba1", "bs1"}, relationship_ids={"r1"}),
    )
    # r1 connects bs1 -> ba1: both selected, so it survives.
    assert result.element_count == 2
    assert result.relationship_count == 1
    root = ET.fromstring(result.xml)
    names = {el.get("name") for el in root.iter()
             if _local(el.tag) in ("businessActor", "businessService")}
    assert names == {"Customer", "Order Management Service"}


def test_export_partial_drops_relationship_with_missing_endpoint(model_32):
    """Relationships with an endpoint outside the selection are dropped."""
    result = ArchiMateExporter().export(
        model_32,
        version="3.2",
        selection=ExportSelection(element_ids={"ba1"}, relationship_ids={"r1"}),
    )
    assert result.relationship_count == 0
    assert any("outside the selection" in w for w in result.warnings)


def test_export_unassigned_elements_get_synthetic_folder(model_32):
    """Elements without a folder land in a synthetic 'Other' folder."""
    model_32.elements["ba1"].folder_id = None
    result = ArchiMateExporter().export(model_32, version="3.2")
    root = ET.fromstring(result.xml)
    folder_names = [el.get("name") for el in root if _local(el.tag) == "folder"]
    assert "Other" in folder_names


def test_export_bad_version_raises(model_32):
    """An unsupported target version raises ExportError."""
    with pytest.raises(ExportError):
        ArchiMateExporter().export(model_32, version="2.0")


def test_export_unknown_selection_ids_warned(model_32):
    """Unknown ids in the selection are ignored with a warning."""
    result = ArchiMateExporter().export(
        model_32,
        version="3.2",
        selection=ExportSelection(element_ids={"ba1", "ghost"}),
    )
    assert result.element_count == 1
    assert any("ghost" in w for w in result.warnings)


def test_folder_has_content_recursive(model_32):
    """folder_has_content checks the folder and its descendants."""
    biz = next(fid for fid, f in model_32.folders.items() if f.name == "Business")
    assert folder_has_content(model_32, biz, {"ba1"}) is True
    assert folder_has_content(model_32, biz, {"nope"}) is False
