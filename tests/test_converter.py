"""Tests for the conversion engine (rules + service + built-ins)."""

from __future__ import annotations

import pytest

from AcheoConverter.core.repository import ModelRepository
from AcheoConverter.exceptions import ConversionError
from AcheoConverter.formalisms.registry import default_registry
from AcheoConverter.services.converter import (
    ConversionRule,
    ConversionRuleRegistry,
    ConversionService,
    build_builtin_rules,
)
from AcheoConverter.services.importer import ImportService


@pytest.fixture()
def importer() -> ImportService:
    return ImportService(default_registry(), max_upload_bytes=10 * 1024 * 1024)


@pytest.fixture()
def service() -> ConversionService:
    registry = ConversionRuleRegistry()
    for rule in build_builtin_rules():
        registry.register(rule)
    return ConversionService(registry)


@pytest.fixture()
def model_32(importer, sample_32):
    repo = ModelRepository()
    result = importer.import_content(sample_32, repository=repo, model_id="m32")
    return repo.get(result.model_id)


@pytest.fixture()
def model_40(importer, sample_40):
    repo = ModelRepository()
    result = importer.import_content(sample_40, repository=repo, model_id="m40")
    return repo.get(result.model_id)


@pytest.fixture()
def model_bpmn(importer, sample_bpmn):
    repo = ModelRepository()
    result = importer.import_content(sample_bpmn, repository=repo, model_id="mbpmn")
    return repo.get(result.model_id)


def test_available_lists_all_built_ins(service):
    """All built-in conversion rules are advertised."""
    available = {c["id"] for c in service.available()}
    assert {
        "archimate-32-to-40", "archimate-40-to-32",
        "bpmn-20-to-archimate-32", "bpmn-20-to-archimate-40",
        "uml-to-archimate-32", "uml-to-archimate-40",
        "sysml-to-archimate-32", "sysml-to-archimate-40",
    } <= available


def test_convert_32_to_40(service, model_32):
    """ArchiMate 3.2 -> 4.0 preserves every element."""
    repo = ModelRepository()
    outcome = service.convert(model_32, target_formalism="archimate",
                              target_version="4.0", repository=repo)
    assert outcome.model_id is not None
    converted = repo.get(outcome.model_id)
    assert converted.metadata.version == "4.0"
    assert len(converted.elements) == len(model_32.elements)
    assert len(converted.relationships) == len(model_32.relationships)
    assert len(converted.folders) == len(model_32.folders)
    assert outcome.report.elements_unmapped == 0
    assert outcome.report.rule_id == "archimate-32-to-40"
    # Names and types survive.
    assert converted.elements["ba1"].name == "Customer"
    assert converted.elements["ba1"].type == "business-actor"


def test_convert_40_to_32_maps_resource(service, model_40):
    """ArchiMate 4.0 -> 3.2 down-maps the 4.0-only Resource concept."""
    repo = ModelRepository()
    outcome = service.convert(model_40, target_formalism="archimate",
                              target_version="3.2", repository=repo)
    converted = repo.get(outcome.model_id)
    assert converted.elements["res1"].type == "technology-resource"
    assert all(e.type in _archimate_32_types() for e in converted.elements.values())


def _archimate_32_types() -> set:
    from AcheoConverter.formalisms.archimate import types as at

    return set(at.ELEMENT_TYPES_32)


def test_convert_dry_run_stores_nothing(service, model_32):
    """dry_run=True produces a report but no stored model."""
    repo = ModelRepository()
    outcome = service.convert(model_32, target_formalism="archimate",
                              target_version="4.0", repository=repo, dry_run=True)
    assert outcome.model_id is None
    assert len(repo) == 0
    assert outcome.report.elements_converted > 0


def test_convert_bpmn_to_archimate(service, model_bpmn):
    """BPMN 2.0 -> ArchiMate maps processes/tasks/flows correctly."""
    repo = ModelRepository()
    outcome = service.convert(model_bpmn, target_formalism="archimate",
                              target_version="3.2", repository=repo)
    converted = repo.get(outcome.model_id)
    assert converted.metadata.formalism == "archimate"
    types = converted.element_types()
    assert "business-process" in types
    assert "business-role" in types  # tasks
    assert "application-function" in types  # serviceTask
    assert "business-event" in types  # events + gateway
    assert "business-actor" in types  # participant
    assert "data-object" in types  # dataObject + dataStore
    # participant gets its documented stereotype.
    assert "participant" in converted.elements["p1"].stereotypes
    # Flows became ArchiMate flows.
    assert converted.relationship_types().get("flow") == 7
    # dataStore is stereotyped.
    assert "data-store" in converted.elements["ds1"].stereotypes
    assert outcome.report.relationships_converted == 7


def test_convert_uml_to_archimate(service, sample_uml, importer):
    """UML -> ArchiMate maps classes/interfaces/activities."""
    repo = ModelRepository()
    imported = importer.import_content(sample_uml, repository=repo, model_id="muml")
    uml_model = repo.get(imported.model_id)
    outcome = service.convert(uml_model, target_formalism="archimate",
                              target_version="3.2", repository=repo)
    converted = repo.get(outcome.model_id)
    assert converted.elements["c1"].type == "business-object"
    assert "class" in converted.elements["c1"].stereotypes
    assert converted.elements["i1"].type == "business-service"
    assert converted.elements["act1"].type == "business-process"
    assert converted.relationships["r1"].type == "realization"
    assert converted.relationships["of1"].type == "flow"


def test_convert_sysml_to_archimate(service, sample_sysml, importer):
    """SysML -> ArchiMate maps blocks/ports/flows."""
    repo = ModelRepository()
    imported = importer.import_content(sample_sysml, repository=repo, model_id="msysml")
    sysml_model = repo.get(imported.model_id)
    outcome = service.convert(sysml_model, target_formalism="archimate",
                              target_version="3.2", repository=repo)
    converted = repo.get(outcome.model_id)
    assert converted.elements["bd1"].type == "application-component"
    assert "block" in converted.elements["bd1"].stereotypes
    assert converted.elements["pd1"].type == "application-service"
    assert converted.relationships["if1"].type == "flow"
    assert converted.relationships["al1"].type == "association"


def test_convert_unsupported_path_raises(service, model_32):
    """Unsupported conversion paths raise ConversionError."""
    repo = ModelRepository()
    with pytest.raises(ConversionError):
        service.convert(model_32, target_formalism="bpmn",
                        target_version="2.0", repository=repo)


def test_convert_invalid_policy_raises(service, model_32):
    """Invalid policy overrides raise ConversionError."""
    repo = ModelRepository()
    with pytest.raises(ConversionError):
        service.convert(model_32, target_formalism="archimate",
                        target_version="4.0", repository=repo,
                        element_policy="explode")


def test_unmapped_element_policies(service, model_32):
    """keep / stereotype / drop policies behave as documented."""
    repo = ModelRepository()

    # stereotype: unknown type -> extension + original-type stereotype.
    rule = ConversionRule(
        id="toy", source_formalism="archimate", source_versions=("3.2",),
        target_formalism="archimate", target_versions=("4.0",),
        element_map={"goal": "goal"},  # everything else unmapped
        element_fallback="stereotype",
    )
    svc = ConversionService(_reg(rule))
    outcome = svc.convert(model_32, target_formalism="archimate",
                          target_version="4.0", repository=repo)
    converted = repo.get(outcome.model_id)
    assert converted.elements["g1"].type == "goal"
    assert converted.elements["ba1"].type == "extension"
    assert "original-type:business-actor" in converted.elements["ba1"].stereotypes

    # drop: unknown type removed.
    rule_drop = ConversionRule(
        id="toy-drop", source_formalism="archimate", source_versions=("3.2",),
        target_formalism="archimate", target_versions=("4.0",),
        element_map={"goal": "goal"}, element_fallback="drop",
    )
    repo2 = ModelRepository()
    outcome2 = ConversionService(_reg(rule_drop)).convert(
        model_32, target_formalism="archimate", target_version="4.0", repository=repo2
    )
    converted2 = repo2.get(outcome2.model_id)
    assert "ba1" not in converted2.elements
    assert outcome2.report.elements_unmapped > 0


def _reg(rule: ConversionRule) -> ConversionRuleRegistry:
    registry = ConversionRuleRegistry()
    registry.register(rule)
    return registry


def test_convert_folders_keep_membership(service, model_32):
    """Conversion keeps folders and their element membership."""
    repo = ModelRepository()
    outcome = service.convert(model_32, target_formalism="archimate",
                              target_version="4.0", repository=repo)
    converted = repo.get(outcome.model_id)
    for folder in model_32.folders.values():
        assert folder.id in converted.folders
        assert converted.folders[folder.id].element_ids == folder.element_ids


def test_convert_provenance_recorded(service, model_bpmn):
    """Converted elements carry __converted_from provenance."""
    repo = ModelRepository()
    outcome = service.convert(model_bpmn, target_formalism="archimate",
                              target_version="3.2", repository=repo)
    converted = repo.get(outcome.model_id)
    provenance = converted.elements["t1"].properties["__converted_from"]
    assert provenance["formalism"] == "bpmn"
    assert provenance["type"] == "task"
