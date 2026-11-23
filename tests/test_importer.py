"""Tests for the import service (detection, normalization, integrity)."""

from __future__ import annotations

import pytest

from ArcheoConverter.core.repository import ModelRepository
from ArcheoConverter.exceptions import (
    ModelAlreadyExistsError,
    ModelImportError,
    PayloadTooLargeError,
    UnsupportedFormalismError,
    UnsupportedVersionError,
)
from ArcheoConverter.formalisms.registry import default_registry
from ArcheoConverter.services.importer import ImportService, _ensure_unique_ids
from ArcheoConverter.core.models import Model, ModelElement, ModelRelationship


@pytest.fixture()
def importer() -> ImportService:
    return ImportService(default_registry(), max_upload_bytes=1024 * 1024)


def test_import_archimate_32(importer, sample_32):
    """The 3.2 sample imports with auto-detection."""
    repo = ModelRepository()
    result = importer.import_content(sample_32, repository=repo, filename="s.archimate")
    assert result.formalism == "archimate"
    assert result.version == "3.2"
    assert result.element_count == 14
    assert result.relationship_count == 9
    assert result.folder_count == 4
    assert repo.contains(result.model_id)
    assert repo.get(result.model_id).metadata.name == "s"  # from the file name


def test_import_bpmn_uml_sysml(importer, sample_bpmn, sample_uml, sample_sysml):
    """The dedicated extensions import through the same service."""
    repo = ModelRepository()
    r1 = importer.import_content(sample_bpmn, repository=repo, filename="p.bpmn")
    r2 = importer.import_content(sample_uml, repository=repo, filename="u.xmi")
    r3 = importer.import_content(sample_sysml, repository=repo, filename="s.xmi")
    assert (r1.formalism, r1.version) == ("bpmn", "2.0")
    assert (r2.formalism, r2.version) == ("uml", "2.5")
    assert (r3.formalism, r3.version) == ("sysml", "1.4")
    assert len(repo) == 3
    # BPMN elements keep their BPMN-native types before conversion.
    bpmn_model = repo.get(r1.model_id)
    assert "process" in bpmn_model.element_types()
    assert "task" in bpmn_model.element_types()


def test_explicit_formalism_and_version(importer, sample_40):
    """An explicit formalism/version override wins over detection."""
    repo = ModelRepository()
    result = importer.import_content(
        sample_40, repository=repo, filename="s.archimate",
        formalism="archimate", version="3.2",
    )
    model = repo.get(result.model_id)
    assert model.metadata.version == "3.2"
    # The 4.0-only resource tag is preserved (as extension) with a warning.
    assert any("resource" in w for w in result.warnings)


def test_duplicate_model_id_raises(importer, sample_32):
    """Importing twice with the same id raises unless overwrite=True."""
    repo = ModelRepository()
    importer.import_content(sample_32, repository=repo, model_id="same")
    with pytest.raises(ModelAlreadyExistsError):
        importer.import_content(sample_32, repository=repo, model_id="same")
    result = importer.import_content(sample_32, repository=repo,
                                     model_id="same", overwrite=True)
    assert result.model_id == "same"
    assert len(repo) == 1


def test_unknown_formalism_raises(importer, sample_32):
    """A forced unknown formalism raises UnsupportedFormalismError."""
    repo = ModelRepository()
    with pytest.raises(UnsupportedFormalismError):
        importer.import_content(sample_32, repository=repo, formalism="eiffel")


def test_unknown_version_raises(importer, sample_32):
    """A forced unknown version raises UnsupportedVersionError."""
    repo = ModelRepository()
    with pytest.raises(UnsupportedVersionError):
        importer.import_content(sample_32, repository=repo,
                                formalism="archimate", version="1.0")


def test_oversized_payload_raises(importer, sample_32):
    """Content above the limit raises PayloadTooLargeError."""
    tiny = ImportService(default_registry(), max_upload_bytes=10)
    repo = ModelRepository()
    with pytest.raises(PayloadTooLargeError):
        tiny.import_content(sample_32, repository=repo)


def test_empty_content_raises(importer):
    """Empty content raises ModelImportError."""
    repo = ModelRepository()
    with pytest.raises(ModelImportError):
        importer.import_content(b"   ", repository=repo)


def test_unrecognized_content_raises(importer):
    """Content no handler recognizes raises UnsupportedFormalismError."""
    repo = ModelRepository()
    with pytest.raises(UnsupportedFormalismError):
        importer.import_content(b"<weird><nothing/></weird>", repository=repo,
                                filename="x.xml")


def test_dangling_relationships_are_reported_not_fatal(importer):
    """Relationships with missing endpoints import with a warning."""
    xml = (
        b'<model xmlns="http://example.com/ns">'
        b"<folder name=\"F\" type=\"other\">"
        b"<node name=\"N\" id=\"a\"/>"
        b"</folder>"
        b"<association id=\"r1\" source=\"a\" target=\"ghost\"/>"
        b"</model>"
    )
    repo = ModelRepository()
    result = importer.import_content(xml, repository=repo)
    assert result.relationship_count == 1
    assert any("ghost" in w for w in result.warnings)


def test_duplicate_ids_are_deduplicated():
    """_ensure_unique_ids renames duplicates and rewrites references."""
    model = Model(
        elements={
            "a": ModelElement(id="a", name="A"),
        },
        relationships={
            "r": ModelRelationship(id="r", source="a", target="a"),
        },
    )
    # Force a collision: a second element reusing id 'a'.
    model.elements["a2"] = ModelElement(id="a", name="A2")
    warnings = _ensure_unique_ids(model)
    ids = set(model.elements)
    assert len(ids) == 2
    assert any("renamed" in w for w in warnings)
    # The relationship endpoints were rewritten consistently.
    rel = model.relationships["r"]
    assert rel.source in ids and rel.target in ids
