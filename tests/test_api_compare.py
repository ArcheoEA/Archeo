"""API tests: model comparison, integration plans and plan application."""

from __future__ import annotations

import pytest

from ArcheoConverter.formalisms.archimate.exporter import ArchiMateExporter


@pytest.fixture()
def two_models(client, sample_32):
    """Import two variants of the 3.2 sample through the API.

    The 'other' variant is produced by mutating a copy of the base model and
    re-serializing it with the exporter (which also exercises export+import).
    """
    client.post_multipart(
        "/api/v1/models",
        fields={"model_id": "cmp-base"},
        files={"file": ("base.archimate", sample_32, "application/xml")},
    )
    repository = client.app.state.app_state.repository
    base = repository.get("cmp-base")
    other = base.model_copy(deep=True)
    other.metadata.name = "Other variant"
    # e1: rename; e2: add stereotype; e3: removed; e4 + r10: added.
    other.elements["ba1"].name = "Client"
    other.elements["bs1"].stereotypes.append("v2")
    del other.elements["ts1"]
    from ArcheoConverter.core.models import ModelElement, ModelRelationship

    other.elements["new1"] = ModelElement(id="new1", name="Backup Service",
                                          type="application-service")
    other.relationships["rel-new"] = ModelRelationship(
        id="rel-new", source="as1", target="new1", type="realization")
    xml, _ = ArchiMateExporter().export(other, version="3.2")
    response = client.post_multipart(
        "/api/v1/models",
        fields={"model_id": "cmp-other"},
        files={"file": ("other.archimate", xml, "application/xml")},
    )
    assert response.status == 201, response.text
    return client


def test_compare_endpoint(two_models):
    """POST /compare returns the full difference report + summary."""
    response = two_models.post_json("/api/v1/compare", {
        "base_id": "cmp-base",
        "other_id": "cmp-other",
    })
    assert response.status == 200, response.text
    data = response.json()
    assert data["report_id"].startswith("cmp-")
    totals = data["result"]["totals"]
    assert totals["elements_added"] == 1
    assert totals["elements_removed"] == 1
    assert totals["elements_modified"] == 2
    assert totals["relationships_added"] == 1
    assert data["summary"]["totals"] == totals
    assert data["result"]["match_by"] == "id_then_name"

    # The report is re-fetchable.
    fetched = two_models.get(f"/api/v1/compare/reports/{data['report_id']}")
    assert fetched.status == 200
    assert fetched.json()["payload"]["totals"] == totals

    listed = two_models.get("/api/v1/compare/reports").json()
    assert any(item["report_id"] == data["report_id"] for item in listed)


def test_compare_different_formalisms(client, sample_32, sample_bpmn):
    """Comparing different formalisms returns 409."""
    client.post_multipart(
        "/api/v1/models", fields={"model_id": "f-arch"},
        files={"file": ("a.archimate", sample_32, "application/xml")})
    client.post_multipart(
        "/api/v1/models", fields={"model_id": "f-bpmn"},
        files={"file": ("b.bpmn", sample_bpmn, "application/xml")})
    response = client.post_json("/api/v1/compare", {
        "base_id": "f-arch", "other_id": "f-bpmn",
    })
    assert response.status == 409
    assert response.json()["code"] == "comparison_error"


def test_integration_plan_endpoint(two_models):
    """POST /compare/integration-plan lists the required modifications."""
    response = two_models.post_json("/api/v1/compare/integration-plan", {
        "base_id": "cmp-base",
        "source_id": "cmp-other",
    })
    assert response.status == 200, response.text
    plan = response.json()["plan"]
    ops = {op["op"] for op in plan["operations"]}
    assert "add_element" in ops        # new1
    assert "add_relationship" in ops   # rel-new
    assert "update_element" in ops     # ba1 rename, bs1 stereotype
    assert "remove_element" not in ops  # additive by default
    assert plan["summary"].get("add_element") == 1

    # include_removals adds the remove operations.
    response = two_models.post_json("/api/v1/compare/integration-plan", {
        "base_id": "cmp-base",
        "source_id": "cmp-other",
        "include_removals": True,
    })
    ops = {op["op"] for op in response.json()["plan"]["operations"]}
    assert "remove_element" in ops


def test_apply_plan_endpoint(two_models):
    """POST /compare/apply merges the source into the base model."""
    before = two_models.get("/api/v1/models/cmp-base").json()
    assert before["element_count"] == 14
    assert before["relationship_count"] == 9

    response = two_models.post_json("/api/v1/compare/apply", {
        "base_id": "cmp-base",
        "source_id": "cmp-other",
    })
    assert response.status == 200, response.text
    data = response.json()
    applied = data["applied"]
    assert applied["skipped"] == 0
    assert applied["applied"] == applied["operations_total"]

    # The merged model: additive merge keeps ts1 and adds new1 (14 -> 15),
    # adds rel-new (9 -> 10), and applies the updates.
    merged = two_models.get("/api/v1/models/cmp-base").json()
    assert merged["element_count"] == 15
    assert merged["relationship_count"] == 10
    elements = two_models.get(
        "/api/v1/models/cmp-base/elements?q=Backup&limit=5").json()
    assert elements["total"] == 1
    detail = two_models.get("/api/v1/models/cmp-base/elements/ba1").json()
    assert detail["element"]["name"] == "Client"
    detail = two_models.get("/api/v1/models/cmp-base/elements/bs1").json()
    assert "v2" in detail["element"]["stereotypes"]
