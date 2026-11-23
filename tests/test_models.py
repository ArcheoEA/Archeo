"""Tests for :mod:`ArcheoConverter.core.models` (in-memory data model)."""

from __future__ import annotations

from ArcheoConverter.core.models import (
    Formalism,
    Model,
    ModelElement,
    ModelFolder,
    ModelMetadata,
    ModelRelationship,
    new_id,
)


def test_new_id_is_unique_and_prefixed():
    """new_id() returns prefixed, unique identifiers."""
    ids = {new_id("el") for _ in range(500)}
    assert len(ids) == 500
    assert all(i.startswith("el-") for i in ids)


def test_element_defaults_and_validation():
    """ModelElement defaults and field normalization."""
    element = ModelElement(id="e1", name="  Customer  ", type="business-actor")
    assert element.name == "Customer"  # stripped
    assert element.stereotypes == []
    assert element.visibility == "public"
    # Unknown visibility values fall back to public.
    weird = ModelElement(id="e2", name="X", type="t", visibility="global")
    assert weird.visibility == "public"
    # Enum members are accepted and normalized to their string value.
    from ArcheoConverter.core.models import Visibility

    enum_visible = ModelElement(id="e3", name="X", type="t", visibility=Visibility.PRIVATE)
    assert enum_visible.visibility == "private"


def test_metadata_formalism_normalization():
    """ModelMetadata.formalism accepts strings (case-insensitive) and enums."""
    metadata = ModelMetadata(name="m", formalism="ARCHIMATE")
    assert metadata.formalism == "archimate"
    metadata2 = ModelMetadata(name="m", formalism=Formalism.BPMN)
    assert metadata2.formalism == "bpmn"
    metadata3 = ModelMetadata(name="m", formalism=42)  # non-str -> unknown
    assert metadata3.formalism == "unknown"


def test_model_helpers():
    """Model accessors and histograms."""
    model = Model(
        metadata=ModelMetadata(model_id="m1", name="Test", formalism="archimate", version="3.2"),
        elements={
            "a": ModelElement(id="a", name="A", type="business-actor"),
            "b": ModelElement(id="b", name="B", type="business-actor"),
            "c": ModelElement(id="c", name="C", type="goal"),
        },
        relationships={
            "r1": ModelRelationship(id="r1", source="a", target="b", type="serving"),
            "r2": ModelRelationship(id="r2", source="c", target="missing", type="influence"),
        },
    )
    assert model.model_id == "m1"
    assert len(model.elements_of_type("business-actor")) == 2
    assert model.element_types() == {"business-actor": 2, "goal": 1}
    assert model.relationship_types() == {"serving": 1, "influence": 1}
    assert model.dangling_relationship_ids() == ["r2"]
    summary = model.summary()
    assert summary["element_count"] == 3
    assert summary["formalism"] == "archimate"
    assert summary["element_types"] == {"business-actor": 2, "goal": 1}


def test_model_deep_copy_isolation():
    """model_copy(deep=True) detaches nested containers."""
    model = Model(
        metadata=ModelMetadata(model_id="m1", name="T"),
        elements={"a": ModelElement(id="a", name="A", stereotypes=["x"])},
    )
    copy = model.model_copy(deep=True)
    copy.elements["a"].stereotypes.append("y")
    copy.metadata.name = "Other"
    assert model.elements["a"].stereotypes == ["x"]
    assert model.metadata.name == "T"


def test_folder_model():
    """ModelFolder basic behavior."""
    folder = ModelFolder(id="f1", name="Business", kind="business")
    assert folder.parent_id is None
    assert folder.element_ids == []
    folder.element_ids.append("a")
    assert folder.element_ids == ["a"]
