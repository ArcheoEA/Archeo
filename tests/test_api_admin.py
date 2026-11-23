"""API tests: administration endpoints (config, stats, purge)."""

from __future__ import annotations


def test_admin_config(client):
    """GET /admin/config returns the effective configuration."""
    response = client.get("/api/v1/admin/config")
    assert response.status == 200
    data = response.json()
    assert data["app_name"] == "AcheoConverter"
    assert data["server"]["port"] == 8000
    assert data["limits"]["max_upload_mb"] == 50
    assert data["ui_enabled"] is True


def test_admin_stats_empty(client):
    """Stats start empty and grow with imports."""
    response = client.get("/api/v1/admin/stats")
    assert response.status == 200
    data = response.json()
    assert data["models"] == 0
    assert data["memory_estimate_bytes"] >= 0
    assert data["uptime_seconds"] >= 0
    assert data["by_formalism"] == {}


def test_admin_stats_after_import(client, sample_32, sample_bpmn):
    """Stats aggregate across loaded models."""
    client.post_multipart(
        "/api/v1/models", fields={"model_id": "s1"},
        files={"file": ("a.archimate", sample_32, "application/xml")})
    client.post_multipart(
        "/api/v1/models", fields={"model_id": "s2"},
        files={"file": ("b.bpmn", sample_bpmn, "application/xml")})
    data = client.get("/api/v1/admin/stats").json()
    assert data["models"] == 2
    # 14 ArchiMate elements + 12 BPMN elements (8 in the process folder
    # incl. the process, 1 participant, 3 data objects/message in General).
    assert data["elements"] == 14 + 12
    assert data["by_formalism"]["archimate:3.2"] == 1
    assert data["by_formalism"]["bpmn:2.0"] == 1


def test_admin_purge(client, sample_32):
    """POST /admin/purge empties the repository."""
    client.post_multipart(
        "/api/v1/models", fields={"model_id": "p1"},
        files={"file": ("a.archimate", sample_32, "application/xml")})
    response = client.post_json("/api/v1/admin/purge", {})
    assert response.status == 200
    assert response.json()["deleted_models"] == 1
    assert client.get("/api/v1/models").json() == []


def test_validation_error_shape(client):
    """Malformed request bodies return a structured 422 payload."""
    response = client.post_json("/api/v1/compare", {"base_id": "x"})  # missing other_id
    assert response.status == 422
    data = response.json()
    assert data["code"] == "validation_error"
    assert isinstance(data["details"], list)
