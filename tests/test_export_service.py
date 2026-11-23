"""Tests for the export service (full / partial / filtered + version target)."""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest

from AcheoConverter.core.repository import ModelRepository
from AcheoConverter.exceptions import ExportError
from AcheoConverter.formalisms.registry import default_registry
from AcheoConverter.services.converter import ConversionRuleRegistry, ConversionService, build_builtin_rules
from AcheoConverter.services.exporter import ExportRequest, ExportService
from AcheoConverter.services.importer import ImportService


@pytest.fixture()
def service() -> ExportService:
    conversions = ConversionRuleRegistry()
    for rule in build_builtin_rules():
        conversions.register(rule)
    converter = ConversionService(conversions)
    return ExportService(converter)


@pytest.fixture()
def importer() -> ImportService:
    return ImportService(default_registry(), max_upload_bytes=10 * 1024 * 1024)


@pytest.fixture()
def model_32(importer, sample_32):
    repo = ModelRepository()
    result = importer.import_content(sample_32, repository=repo, model_id="m32")
    return repo.get(result.model_id)


def test_full_export(service, model_32):
    """A full export includes everything."""
    xml, report = service.export(model_32, ExportRequest(scope="full"))
    assert report.element_count == 14
    assert report.relationship_count == 9
    assert report.folder_count == 4
    assert report.converted is False
    assert xml.decode("utf-8").startswith("<?xml")


def test_partial_export_by_ids(service, model_32):
    """Partial scope exports the selected ids (and their inner relations)."""
    xml, report = service.export(model_32, ExportRequest(
        scope="partial",
        element_ids=["ba1", "bs1"],
        relationship_ids=["r1"],
    ))
    assert report.element_count == 2
    assert report.relationship_count == 1  # r1 (both endpoints selected)
    root = ET.fromstring(xml)
    names = {el.get("name") for el in root.iter()
             if isinstance(el.tag, str) and "business" in el.tag}
    assert "Customer" in names


def test_partial_export_by_folder(service, model_32):
    """Partial scope can select whole folders (element closure)."""
    biz = next(fid for fid, f in model_32.folders.items() if f.name == "Business")
    xml, report = service.export(model_32, ExportRequest(
        scope="partial", folder_ids=[biz],
    ))
    # The Business folder holds ba1, bs1, bp1, br1, bo1 (5 elements).
    assert report.element_count == 5
    # Relationships with both endpoints inside: r2 (bp1->br1), r4 (bp1->bo1),
    # r1 (bs1->ba1) => 3.
    assert report.relationship_count == 3


def test_filtered_export_by_type_and_regex(service, model_32):
    """Filtered scope applies type + regex + stereotype filters."""
    xml, report = service.export(model_32, ExportRequest(
        scope="filtered",
        element_types=["business-actor", "business-service"],
        name_regex="^Order",
    ))
    # business-service "Order Management Service" + no business-actor matches.
    assert report.element_count == 1

    xml2, report2 = service.export(model_32, ExportRequest(
        scope="filtered", stereotypes=["External"],
    ))
    assert report2.element_count == 1  # Customer


def test_filtered_export_empty_selection_raises(service, model_32):
    """A filter matching nothing raises ExportError."""
    with pytest.raises(ExportError):
        service.export(model_32, ExportRequest(
            scope="filtered", element_types=["goal"], name_regex="^Impossible.*XYZ",
        ))


def test_export_converts_to_40_first(service, model_32):
    """target_version=4.0 converts in memory before exporting."""
    xml, report = service.export(model_32, ExportRequest(scope="full", target_version="4.0"))
    assert report.converted is True
    assert report.target_version == "4.0"
    assert report.version == "3.2"
    assert any("converted" in w.lower() for w in report.warnings)
    # Document is valid XML with the model root.
    root = ET.fromstring(xml)
    assert root.tag.endswith("}model")


def test_export_40_to_32_maps_resource(service, importer, sample_40):
    """Exporting a 4.0 model to 3.2 down-maps the Resource concept."""
    repo = ModelRepository()
    result = importer.import_content(sample_40, repository=repo, model_id="m40")
    model_40 = repo.get(result.model_id)
    xml, report = service.export(model_40, ExportRequest(scope="full", target_version="3.2"))
    root = ET.fromstring(xml)
    tags = {el.tag.rsplit("}", 1)[-1] for el in root.iter() if isinstance(el.tag, str)}
    assert "resource" not in tags
    assert "technologyResource" in tags


def test_export_bad_version_raises(service, model_32):
    """An unsupported target version raises ExportError."""
    with pytest.raises(ExportError):
        service.export(model_32, ExportRequest(scope="full", target_version="9.9"))


def test_export_invalid_regex_raises(service, model_32):
    """An invalid name regex raises ExportError (not a 500)."""
    with pytest.raises(ExportError):
        service.export(model_32, ExportRequest(scope="filtered", name_regex="("))


def test_export_unknown_ids_warned(service, model_32):
    """Unknown ids in a partial selection are ignored with a warning."""
    xml, report = service.export(model_32, ExportRequest(
        scope="partial", element_ids=["ba1", "ghost"],
    ))
    assert report.element_count == 1
    assert any("ghost" in w for w in report.warnings)


def test_export_non_archimate_raises(service, importer, sample_bpmn):
    """Exporting a non-ArchiMate model raises ExportError."""
    repo = ModelRepository()
    result = importer.import_content(sample_bpmn, repository=repo, model_id="mbpmn")
    bpmn_model = repo.get(result.model_id)
    with pytest.raises(ExportError):
        service.export(bpmn_model, ExportRequest(scope="full"))
