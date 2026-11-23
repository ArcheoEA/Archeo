"""Tests for :mod:`AcheoConverter.config` (layered configuration)."""

from __future__ import annotations

import json

import pytest

from AcheoConverter.config import load_config
from AcheoConverter.exceptions import ConfigError


def test_defaults_when_no_source(tmp_path, monkeypatch):
    """With no file and no env vars, built-in defaults are returned."""
    monkeypatch.delenv("ACHEOCONVERTER_CONFIG", raising=False)
    (tmp_path / "config").mkdir(exist_ok=True)
    monkeypatch.chdir(tmp_path)  # ensure config/app.json is not found
    config = load_config()
    assert config.app_name == "AcheoConverter"
    assert config.server.port == 8000
    assert config.limits.max_upload_mb == 50
    assert config.ui_enabled is True


def test_json_file_loading(tmp_path, monkeypatch):
    """A JSON configuration file is loaded and merged over defaults."""
    config_file = tmp_path / "app.json"
    config_file.write_text(
        json.dumps({"server": {"port": 9999}, "ui_enabled": False}),
        encoding="utf-8",
    )
    monkeypatch.delenv("ACHEOCONVERTER_CONFIG", raising=False)
    config = load_config(config_file)
    assert config.server.port == 9999
    assert config.ui_enabled is False
    # Untouched sections keep their defaults.
    assert config.limits.max_graph_nodes == 2000


def test_env_file_discovery(tmp_path, monkeypatch):
    """$ACHEOCONVERTER_CONFIG is used when no explicit path is given."""
    config_file = tmp_path / "custom.json"
    config_file.write_text(json.dumps({"server": {"host": "127.0.0.1"}}), encoding="utf-8")
    monkeypatch.setenv("ACHEOCONVERTER_CONFIG", str(config_file))
    config = load_config()
    assert config.server.host == "127.0.0.1"


def test_env_var_overrides(tmp_path, monkeypatch):
    """ACHEOCONVERTER__* environment variables override file values."""
    config_file = tmp_path / "app.json"
    config_file.write_text(json.dumps({"server": {"port": 9000}}), encoding="utf-8")
    monkeypatch.setenv("ACHEOCONVERTER__SERVER__PORT", "1234")
    monkeypatch.setenv("ACHEOCONVERTER__UI_ENABLED", "false")
    monkeypatch.setenv("ACHEOCONVERTER__LIMITS__MAX_UPLOAD_MB", "5")
    config = load_config(config_file)
    assert config.server.port == 1234
    assert config.ui_enabled is False
    assert config.limits.max_upload_mb == 5


def test_invalid_file_raises(tmp_path):
    """An unreadable / non-object JSON file raises ConfigError."""
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(bad)


def test_invalid_value_raises(tmp_path):
    """A value violating the schema raises ConfigError."""
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"server": {"port": 99999}}), encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(bad)


def test_namespace_for():
    """namespace_for() resolves formalism:version and per-formalism fallbacks."""
    config = AppConfig()
    config.formalisms.namespaces = {"archimate:3.2": "http://ns/32", "bpmn:2.0": "http://ns/bpmn"}
    assert config.namespace_for("archimate", "3.2") == "http://ns/32"
    # 4.0 has no explicit entry -> falls back to the archimate one.
    assert config.namespace_for("archimate", "4.0") == "http://ns/32"
    # Unknown formalism -> empty string.
    assert config.namespace_for("nope", "1.0") == ""
