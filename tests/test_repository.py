"""Tests for :mod:`AcheoConverter.core.repository` (in-memory repository)."""

from __future__ import annotations

import pytest

from AcheoConverter.core.models import Model, ModelElement, ModelMetadata
from AcheoConverter.core.repository import ModelRepository, ReportStore, estimate_bytes
from AcheoConverter.exceptions import (
    ModelAlreadyExistsError,
    ModelNotFoundError,
    ReportNotFoundError,
)


def _model(model_id: str, name: str = "m") -> Model:
    return Model(
        metadata=ModelMetadata(model_id=model_id, name=name),
        elements={"a": ModelElement(id="a", name="A")},
    )


def test_add_and_get():
    """add() stores a model; get() retrieves it by id."""
    repo = ModelRepository()
    model = _model("m1", "First")
    repo.add(model)
    assert repo.get("m1") is model
    assert len(repo) == 1
    assert repo.contains("m1")


def test_duplicate_add_raises_unless_overwrite():
    """A duplicate id raises unless overwrite=True / replace() is used."""
    repo = ModelRepository()
    repo.add(_model("m1"))
    with pytest.raises(ModelAlreadyExistsError):
        repo.add(_model("m1"))
    repo.add(_model("m1", "Second"), overwrite=True)
    assert repo.get("m1").metadata.name == "Second"
    repo.replace(_model("m1", "Third"))
    assert repo.get("m1").metadata.name == "Third"


def test_get_missing_raises():
    """get() on an unknown id raises ModelNotFoundError (404)."""
    repo = ModelRepository()
    with pytest.raises(ModelNotFoundError):
        repo.get("nope")


def test_remove_and_clear():
    """remove() and clear() return accurate counts."""
    repo = ModelRepository()
    repo.add(_model("m1"))
    repo.add(_model("m2"))
    assert repo.remove("m1") is True
    assert repo.remove("m1") is False
    assert repo.clear() == 1
    assert len(repo) == 0


def test_list_sorted_by_import_date():
    """list() returns models in import date order."""
    repo = ModelRepository()
    repo.add(_model("m1"))
    repo.add(_model("m2"))
    listed = repo.list()
    assert [m.model_id for m in listed] == ["m1", "m2"]


def test_stats():
    """stats() aggregates counts and per-formalism breakdowns."""
    repo = ModelRepository()
    repo.add(_model("m1"))
    repo.add(
        Model(
            metadata=ModelMetadata(model_id="m2", name="bpmn model", formalism="bpmn", version="2.0"),
            elements={},
        )
    )
    stats = repo.stats()
    assert stats["models"] == 2
    assert stats["elements"] == 1
    assert stats["by_formalism"]["bpmn:2.0"] == 1
    assert stats["by_formalism"]["unknown:?"] == 1
    assert stats["memory_estimate_bytes"] > 0


def test_estimate_bytes():
    """estimate_bytes() accounts for nested containers."""
    small = estimate_bytes({"a": 1})
    big = estimate_bytes({"a": list(range(1000))})
    assert big > small


def test_report_store():
    """ReportStore keeps transient reports by id."""
    store = ReportStore()
    store.store("r1", "comparison", {"x": 1})
    store.store("r2", "plan", {"y": 2})
    assert store.get("r1")["payload"] == {"x": 1}
    assert store.count() == 2
    assert [item["report_id"] for item in store.list("comparison")] == ["r1"]
    assert store.clear("plan") == 1
    with pytest.raises(ReportNotFoundError):
        store.get("missing")
