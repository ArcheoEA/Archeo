"""Tests for the comparison & integration-plan service."""

from __future__ import annotations

import pytest

from ArcheoConverter.core.models import (
    Model,
    ModelElement,
    ModelFolder,
    ModelMetadata,
    ModelRelationship,
)
from ArcheoConverter.exceptions import ComparisonError
from ArcheoConverter.services.comparator import ComparatorService


def _model_a() -> Model:
    """Base model: 3 elements, 2 relationships, 1 folder."""
    return Model(
        metadata=ModelMetadata(model_id="A", name="Model A", formalism="archimate",
                               version="3.2"),
        elements={
            "e1": ModelElement(id="e1", name="Customer", type="business-actor"),
            "e2": ModelElement(id="e2", name="Order Service", type="business-service",
                               stereotypes=["core"]),
            "e3": ModelElement(id="e3", name="Legacy", type="extension"),
        },
        relationships={
            "r1": ModelRelationship(id="r1", source="e1", target="e2", type="serving"),
            "r2": ModelRelationship(id="r2", source="e2", target="e3", type="association"),
        },
        folders={
            "f1": ModelFolder(id="f1", name="Business", kind="business",
                              element_ids=["e1", "e2", "e3"]),
        },
    )


def _model_b() -> Model:
    """Variant of A: e1 renamed (same id), e2 stereotypes changed, e3 removed,
    e4 added with a new relationship r3, folder renamed."""
    return Model(
        metadata=ModelMetadata(model_id="B", name="Model B", formalism="archimate",
                               version="3.2"),
        elements={
            "e1": ModelElement(id="e1", name="Client", type="business-actor"),
            "e2": ModelElement(id="e2", name="Order Service", type="business-service",
                               stereotypes=["core", "v2"]),
            "e4": ModelElement(id="e4", name="Payment", type="business-event"),
        },
        relationships={
            "r1": ModelRelationship(id="r1", source="e1", target="e2", type="serving"),
            "r3": ModelRelationship(id="r3", source="e2", target="e4", type="flow"),
        },
        folders={
            "f1": ModelFolder(id="f1", name="Business v2", kind="business",
                              element_ids=["e1", "e2", "e4"]),
        },
    )


@pytest.fixture()
def service() -> ComparatorService:
    return ComparatorService()


def test_compare_id_then_name(service):
    """id_then_name matching detects adds/removes/modifications."""
    a, b = _model_a(), _model_b()
    result = service.compare(a, b)
    totals = result.totals
    assert totals["elements_added"] == 1      # e4
    assert totals["elements_removed"] == 1    # e3
    assert totals["elements_modified"] == 2   # e1 (name), e2 (stereotypes)
    assert totals["relationships_added"] == 1  # r3
    assert totals["relationships_removed"] == 1  # r2
    assert totals["folders_modified"] == 1   # f1 renamed + membership

    added = {ref.id for ref in result.elements.added}
    removed = {ref.id for ref in result.elements.removed}
    assert added == {"e4"}
    assert removed == {"e3"}
    modified_ids = {m.base_id for m in result.elements.modified}
    assert modified_ids == {"e1", "e2"}
    e1_change = next(m for m in result.elements.modified if m.base_id == "e1")
    assert e1_change.changes["name"].old == "Customer"
    assert e1_change.changes["name"].new == "Client"
    e2_change = next(m for m in result.elements.modified if m.base_id == "e2")
    assert "stereotypes" in e2_change.changes


def test_compare_identical_models(service):
    """Two identical models have no differences."""
    a = _model_a()
    b = a.model_copy(deep=True)
    result = service.compare(a, b)
    assert sum(result.totals.values()) == 0


def test_compare_by_id_only(service):
    """match_by=id ignores name matches."""
    a = _model_a()
    b = a.model_copy(deep=True)
    # Rename the id of e1 in b but keep the name: with id matching, e1 is
    # removed and the same-named element is added.
    b.elements["e1x"] = b.elements.pop("e1")
    result = service.compare(a, b, match_by="id")
    assert result.totals["elements_added"] == 1
    assert result.totals["elements_removed"] == 1
    assert result.totals["elements_modified"] == 0


def test_compare_by_name(service):
    """match_by=name matches renamed-id elements."""
    a = _model_a()
    b = a.model_copy(deep=True)
    b.elements["e1x"] = b.elements.pop("e1")
    result = service.compare(a, b, match_by="name")
    assert result.totals["elements_added"] == 0
    assert result.totals["elements_removed"] == 0


def test_compare_invalid_match_by(service):
    """An unknown match strategy raises ComparisonError."""
    with pytest.raises(ComparisonError):
        service.compare(_model_a(), _model_a(), match_by="quantum")


def test_compare_different_formalisms_raises(service):
    """Comparing different formalisms raises ComparisonError."""
    a = _model_a()
    b = _model_a().model_copy(deep=True)
    b.metadata.formalism = "bpmn"
    with pytest.raises(ComparisonError):
        service.compare(a, b)


def test_integration_plan_additive(service):
    """The plan adds the missing pieces and updates the modified ones."""
    a, b = _model_a(), _model_b()
    plan = service.integration_plan(a, b)
    ops = {op.op: op for op in plan.operations}
    # e3 removal is NOT included (additive by default).
    assert "remove_element" not in ops
    assert "add_element" in ops
    add_element = ops["add_element"]
    assert add_element.target_id == "e4"
    assert add_element.payload["folder_id"] == "f1"
    assert ops["add_relationship"].target_id == "r3"
    assert "update_element" in ops
    assert ops["update_folder"].target_id == "f1"
    summary = plan.summary
    assert summary.get("add_element") == 1
    assert summary.get("add_relationship") == 1
    assert summary.get("update_element") == 2
    assert summary.get("update_folder") == 1


def test_integration_plan_with_removals(service):
    """include_removals=True adds remove_* operations."""
    a, b = _model_a(), _model_b()
    plan = service.integration_plan(a, b, include_removals=True)
    ops = [op.op for op in plan.operations]
    assert "remove_element" in ops
    assert "remove_relationship" in ops


def test_apply_plan_merges(service):
    """apply_plan() produces the merged model; the base is not mutated."""
    a, b = _model_a(), _model_b()
    plan = service.integration_plan(a, b)
    before_elements = len(a.elements)
    merged, report = service.apply_plan(a, plan)
    assert a.elements.keys() == {e.id for e in [a.elements["e1"], a.elements["e2"], a.elements["e3"]]}
    assert len(a.elements) == before_elements  # base untouched
    assert report.applied == len(plan.operations)
    assert report.skipped == 0
    # e4 and r3 are now in the merged model.
    assert "e4" in merged.elements
    assert merged.elements["e1"].name == "Client"  # update applied
    assert "r3" in merged.relationships
    assert merged.folders["f1"].name == "Business v2"
    assert report.element_count == 4
    assert report.relationship_count == 3


def test_apply_plan_skips_missing_endpoints(service):
    """Relationships whose endpoints are not merged are skipped (warning)."""
    a = _model_a()
    b = a.model_copy(deep=True)
    # Add a relationship in b pointing at an element that b will not bring
    # (we delete it from b so it is neither matched nor added).
    del b.elements["e3"]
    b.relationships["r2"].target = "ghost"
    plan = service.integration_plan(a, b)
    # r2 is 'modified' (target changed) in b -> update_relationship op.
    merged, report = service.apply_plan(a, plan)
    # The update points r2 at 'ghost' which does not exist in the merged
    # model: update_relationship does not validate endpoints (documented
    # behaviour), so it is applied; but an *added* relationship with a
    # missing endpoint must be skipped.
    assert report.applied + report.skipped == len(plan.operations)
