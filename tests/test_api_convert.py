"""API tests: model conversion endpoints."""

from __future__ import annotations

import pytest


@pytest.fixture()
def client_32(client, sample_32):
    response = client.post_multipart(
        "/api/v1/models",
        fields={"model_id": "conv-32"},
        files={"file": ("s32.archimate", sample_32, "application/xml")},
    )
    assert response.status == 201
    return client


def test_available_conversions(client):
    """GET /convert/available lists the built-in rules."""
    response = client.get("/api/v1/convert/available")
    assert response.status == 200
    rules = {r["id"]: r for r in response.json()}
    assert "archimate-32-to-40" in rules
    assert "bpmn-20-to-archimate-40" in rules
    rule = rules["archimate-32-to-40"]
    assert rule["source_formalism"] == "archimate"
    assert rule["target_versions"] == ["4.0"]


def test_convert_32_to_40(client_32):
    """POST /convert performs the migration and stores the new model."""
    response = client_32.post_json("/api/v1/convert", {
        "model_id": "conv-32",
        "target_formalism": "archimate",
        "target_version": "4.0",
    })
    assert response.status == 200, response.text
    data = response.json()
    assert data["model_id"] is not None
    assert data["report"]["rule_id"] == "archimate-32-to-40"
    assert data["report"]["elements_converted"] == 14
    assert data["report"]["elements_unmapped"] == 0

    # The converted model is now loadable.
    detail = client_32.get(f"/api/v1/models/{data['model_id']}")
    assert detail.status == 200
    assert detail.json()["version"] == "4.0"

    # The source model is unchanged.
    assert client_32.get("/api/v1/models/conv-32").json()["version"] == "3.2"


def test_convert_dry_run(client_32):
    """dry_run=true reports without storing."""
    before = len(client_32.get("/api/v1/models").json())
    response = client_32.post_json("/api/v1/convert", {
        "model_id": "conv-32",
        "target_formalism": "archimate",
        "target_version": "4.0",
        "dry_run": True,
    })
    assert response.status == 200
    assert response.json()["model_id"] is None
    after = len(client_32.get("/api/v1/models").json())
    assert before == after


def test_convert_bpmn_to_archimate(client, sample_bpmn):
    """Cross-formalism migration: BPMN 2.0 -> ArchiMate 3.2."""
    client.post_multipart(
        "/api/v1/models",
        fields={"model_id": "conv-bpmn"},
        files={"file": ("p.bpmn", sample_bpmn, "application/xml")},
    )
    response = client.post_json("/api/v1/convert", {
        "model_id": "conv-bpmn",
        "target_formalism": "archimate",
        "target_version": "3.2",
        "name": "Order process (archimate)",
    })
    assert response.status == 200, response.text
    data = response.json()
    assert data["report"]["elements_converted"] >= 10
    new_id = data["model_id"]
    detail = client.get(f"/api/v1/models/{new_id}").json()
    assert detail["formalism"] == "archimate"
    assert detail["name"] == "Order process (archimate)"


def test_convert_unsupported_path(client_32):
    """An unsupported conversion path returns 422 with details."""
    response = client_32.post_json("/api/v1/convert", {
        "model_id": "conv-32",
        "target_formalism": "bpmn",
        "target_version": "2.0",
    })
    assert response.status == 422
    assert response.json()["code"] == "conversion_error"


def test_convert_unknown_model(client_32):
    """Converting a missing model returns 404."""
    response = client_32.post_json("/api/v1/convert", {
        "model_id": "nope",
        "target_formalism": "archimate",
        "target_version": "4.0",
    })
    assert response.status == 404
    assert response.json()["code"] == "model_not_found"
