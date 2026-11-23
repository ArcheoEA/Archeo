"""API tests: model import, listing, navigation, visualization, summary."""

from __future__ import annotations

import pytest

from AcheoConverter.api.routers.models import router  # noqa: F401 - import check


@pytest.fixture()
def client_with_32(client, sample_32):
    """A client with the ArchiMate 3.2 sample already imported via the API."""
    response = client.post_multipart(
        "/api/v1/models",
        fields={"model_id": "api-32", "name": "API Sample 3.2"},
        files={"file": ("sample_32.archimate", sample_32, "application/xml")},
    )
    assert response.status == 201, response.text
    return client


def test_meta(client):
    """GET /meta reports the application capabilities."""
    response = client.get("/api/v1/meta")
    assert response.status == 200
    data = response.json()
    assert data["app"] == "AcheoConverter"
    formalisms = {(f["formalism"], f["version"]) for f in data["formalisms"]}
    assert ("archimate", "3.2") in formalisms
    assert ("archimate", "4.0") in formalisms
    assert ("bpmn", "2.0") in formalisms
    assert ("uml", "2.5") in formalisms
    assert ("sysml", "1.4") in formalisms
    assert len(data["conversions"]) >= 8
    assert data["openapi"] == "/openapi.json"


def test_openapi_documentation(client):
    """The OpenAPI document is generated and importable by API tooling."""
    response = client.get("/openapi.json")
    assert response.status == 200
    spec = response.json()
    assert spec["openapi"].startswith("3.")
    paths = spec["paths"]
    assert "/api/v1/models" in paths
    assert "/api/v1/convert" in paths
    assert "/api/v1/compare" in paths
    assert "/api/v1/admin/stats" in paths


def test_health(client):
    """GET /health is a liveness probe."""
    response = client.get("/health")
    assert response.status == 200
    assert response.json()["status"] == "ok"


def test_upload_import_and_list(client, sample_32, sample_40):
    """Multipart upload imports; GET /models lists with counts."""
    response = client.post_multipart(
        "/api/v1/models",
        fields={"model_id": "api-32"},
        files={"file": ("s32.archimate", sample_32, "application/xml")},
    )
    assert response.status == 201
    data = response.json()
    assert data["formalism"] == "archimate"
    assert data["version"] == "3.2"
    assert data["element_count"] == 14
    assert data["relationship_count"] == 9
    assert data["folder_count"] == 4

    client.post_multipart(
        "/api/v1/models",
        fields={"model_id": "api-40"},
        files={"file": ("s40.archimate", sample_40, "application/xml")},
    )
    listed = client.get("/api/v1/models").json()
    assert len(listed) == 2
    assert {m["model_id"] for m in listed} == {"api-32", "api-40"}


def test_upload_duplicate_id_conflict(client_with_32, sample_32):
    """Re-importing the same id without overwrite returns 409."""
    response = client_with_32.post_multipart(
        "/api/v1/models",
        fields={"model_id": "api-32"},
        files={"file": ("s32.archimate", sample_32, "application/xml")},
    )
    assert response.status == 409
    assert response.json()["code"] == "model_already_exists"


def test_upload_bad_xml_conflict(client):
    """Malformed XML returns 422 with a domain error code."""
    response = client.post_multipart(
        "/api/v1/models",
        fields={},
        files={"file": ("bad.xml", b"<broken", "application/xml")},
    )
    assert response.status == 422
    assert response.json()["code"] == "model_import_error"


def test_json_import_endpoint(client, sample_32):
    """POST /models/import accepts raw or base64 content."""
    response = client.post_json("/api/v1/models/import", {
        "model_id": "json-32",
        "name": "JSON import",
        "filename": "s.archimate",
        "content": sample_32.decode("utf-8"),
    })
    assert response.status == 201
    assert response.json()["element_count"] == 14

    # Both content and content_base64 -> 422.
    response = client.post_json("/api/v1/models/import", {
        "model_id": "x", "content": "a", "content_base64": "a",
    })
    assert response.status == 422


def test_model_detail_and_summary(client_with_32):
    """GET /models/{id} returns metadata + structured summary."""
    response = client_with_32.get("/api/v1/models/api-32")
    assert response.status == 200
    data = response.json()
    assert data["element_count"] == 14
    assert data["summary"]["elements_by_type"]["business-actor"] == 1
    assert data["summary"]["dangling_relationships"] == []
    assert len(data["summary"]["folders"]) == 4

    response = client_with_32.get("/api/v1/models/api-32/summary")
    assert response.status == 200
    summary = response.json()
    assert summary["model_id"] == "api-32"

    response = client_with_32.get("/api/v1/models/api-32/summary/markdown")
    assert response.status == 200
    assert "# Model summary" in response.text


def test_search_elements(client_with_32):
    """Element search supports text, type and pagination."""
    response = client_with_32.get(
        "/api/v1/models/api-32/elements?q=order&limit=10")
    assert response.status == 200
    page = response.json()
    assert page["total"] >= 3
    names = {item["name"] for item in page["items"]}
    assert "Order Management Service" in names

    response = client_with_32.get(
        "/api/v1/models/api-32/elements?types=business-actor")
    page = response.json()
    assert page["total"] == 1
    assert page["items"][0]["id"] == "ba1"

    # Stereotype filter.
    response = client_with_32.get(
        "/api/v1/models/api-32/elements?stereotypes=External")
    assert response.json()["total"] == 1


def test_element_detail_with_links(client_with_32):
    """Element detail includes inbound/outbound relationships."""
    response = client_with_32.get("/api/v1/models/api-32/elements/bs1")
    assert response.status == 200
    data = response.json()
    assert data["element"]["id"] == "bs1"
    assert data["outbound"][0]["id"] == "r1"
    assert data["inbound"][0]["id"] == "r3"

    # Unknown element -> 404.
    response = client_with_32.get("/api/v1/models/api-32/elements/nope")
    assert response.status == 404


def test_relationships_listing(client_with_32):
    """Relationships can be filtered by type/source/target."""
    response = client_with_32.get("/api/v1/models/api-32/relationships")
    assert response.json()["total"] == 9
    response = client_with_32.get(
        "/api/v1/models/api-32/relationships?type=aggregation")
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == "r6"
    response = client_with_32.get(
        "/api/v1/models/api-32/relationships?source=bs1")
    assert response.json()["total"] == 1


def test_folders_tree_and_content(client_with_32):
    """The folder tree nests correctly; folder content lists entities."""
    response = client_with_32.get("/api/v1/models/api-32/folders")
    assert response.status == 200
    tree = response.json()["tree"]
    names = {node["name"] for node in tree}
    assert {"Strategy", "Business", "Application", "Technology"} == names
    business = next(n for n in tree if n["name"] == "Business")
    assert business["element_count"] == 5

    response = client_with_32.get(f"/api/v1/models/api-32/folders/{business['id']}")
    assert response.status == 200
    content = response.json()
    assert len(content["elements"]) == 5
    # r2 (bp1->br1) and r4 (bp1->bo1) and r1 (bs1->ba1) are inside.
    assert len(content["relationships"]) == 3


def test_graph_endpoints(client_with_32):
    """Graph payloads for whole model, folder and neighborhood."""
    response = client_with_32.get("/api/v1/models/api-32/graph")
    assert response.status == 200
    payload = response.json()
    assert len(payload["nodes"]) == 14
    assert len(payload["edges"]) == 9

    tree = client_with_32.get("/api/v1/models/api-32/folders").json()["tree"]
    tech = next(n for n in tree if n["name"] == "Technology")
    response = client_with_32.get(
        f"/api/v1/models/api-32/graph?folder={tech['id']}")
    payload = response.json()
    assert len(payload["nodes"]) == 3

    response = client_with_32.get(
        "/api/v1/models/api-32/graph?from=bs1&depth=1")
    payload = response.json()
    node_ids = {n["id"] for n in payload["nodes"]}
    assert node_ids == {"bs1", "ba1", "bp1", "as1"}


def test_delete_model(client_with_32):
    """DELETE removes the model; a second DELETE returns 404."""
    response = client_with_32.delete("/api/v1/models/api-32")
    assert response.status == 204
    assert client_with_32.get("/api/v1/models/api-32").status == 404
    assert client_with_32.delete("/api/v1/models/api-32").status == 404
