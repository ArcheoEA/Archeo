"""API tests: model export endpoints (XML + JSON envelopes)."""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest


@pytest.fixture()
def client_32(client, sample_32):
    response = client.post_multipart(
        "/api/v1/models",
        fields={"model_id": "exp-32"},
        files={"file": ("s32.archimate", sample_32, "application/xml")},
    )
    assert response.status == 201
    return client


def test_export_full_xml(client_32):
    """POST /models/{id}/export returns an XML document."""
    response = client_32.post_json("/api/v1/models/exp-32/export", {"scope": "full"})
    assert response.status == 200
    assert response.header("content-type").startswith("application/xml")
    assert "attachment" in (response.header("content-disposition") or "")
    text = response.text
    assert text.startswith("<?xml")
    root = ET.fromstring(text)
    assert root.tag.endswith("}model")
    # The report travels in a header (JSON).
    import json

    report = json.loads(response.header("x-export-report"))
    assert report["element_count"] == 14
    assert report["relationship_count"] == 9
    assert report["folder_count"] == 4


def test_export_partial_json_envelope(client_32):
    """format=json returns the report + XML text in one payload."""
    response = client_32.post_json("/api/v1/models/exp-32/export?format=json", {
        "scope": "partial",
        "element_ids": ["ba1", "bs1"],
        "relationship_ids": ["r1"],
    })
    assert response.status == 200
    data = response.json()
    assert data["report"]["element_count"] == 2
    assert data["report"]["relationship_count"] == 1
    assert data["xml"].startswith("<?xml")
    assert data["markdown"].startswith("# Model summary")


def test_export_filtered(client_32):
    """Filtered export respects type + regex + stereotype filters."""
    response = client_32.post_json("/api/v1/models/exp-32/export?format=json", {
        "scope": "filtered",
        "element_types": ["business-actor", "business-service"],
        "name_regex": "^Order",
    })
    assert response.status == 200
    assert response.json()["report"]["element_count"] == 1

    response = client_32.post_json("/api/v1/models/exp-32/export?format=json", {
        "scope": "filtered",
        "stereotypes": ["External"],
    })
    assert response.json()["report"]["element_count"] == 1


def test_export_converted_target_version(client_32):
    """Exporting to a different version converts in memory first."""
    response = client_32.post_json("/api/v1/models/exp-32/export?format=json", {
        "scope": "full",
        "target_version": "4.0",
    })
    assert response.status == 200
    report = response.json()["report"]
    assert report["converted"] is True
    assert report["target_version"] == "4.0"


def test_export_errors(client_32):
    """Invalid requests return 422 domain errors."""
    # Invalid scope.
    response = client_32.post_json("/api/v1/models/exp-32/export", {"scope": "weird"})
    assert response.status == 422
    assert response.json()["code"] == "export_error"
    # Invalid regex.
    response = client_32.post_json("/api/v1/models/exp-32/export", {
        "scope": "filtered", "name_regex": "(",
    })
    assert response.status == 422
    # Empty selection.
    response = client_32.post_json("/api/v1/models/exp-32/export", {
        "scope": "filtered", "name_regex": "^Impossible.*XYZ",
    })
    assert response.status == 422
    # Unknown model.
    response = client_32.post_json("/api/v1/models/nope/export", {"scope": "full"})
    assert response.status == 404


def test_export_non_archimate_rejected(client, sample_bpmn):
    """Non-ArchiMate models cannot be exported directly (convert first)."""
    client.post_multipart(
        "/api/v1/models",
        fields={"model_id": "exp-bpmn"},
        files={"file": ("p.bpmn", sample_bpmn, "application/xml")},
    )
    response = client.post_json("/api/v1/models/exp-bpmn/export", {"scope": "full"})
    assert response.status == 422
    assert response.json()["code"] == "export_error"
