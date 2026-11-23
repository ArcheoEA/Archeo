"""Tests for the search & navigation service."""

from __future__ import annotations

import pytest

from AcheoConverter.core.models import (
    Model,
    ModelElement,
    ModelFolder,
    ModelMetadata,
    ModelRelationship,
)
from AcheoConverter.exceptions import GraphTooLargeError, ModelNotFoundError
from AcheoConverter.services.search import SearchService


def _big_model() -> Model:
    """A small hand-built model covering several types/folders."""
    model = Model(
        metadata=ModelMetadata(model_id="big", name="Big", formalism="archimate",
                               version="3.2"),
        elements={
            "ba1": ModelElement(id="ba1", name="Customer", type="business-actor",
                                stereotypes=["External"]),
            "ba2": ModelElement(id="ba2", name="Order Customer", type="business-actor"),
            "bs1": ModelElement(id="bs1", name="Order Service", type="business-service"),
            "bp1": ModelElement(id="bp1", name="Order Processing", type="business-process"),
            "as1": ModelElement(id="as1", name="Order API", type="application-service"),
            "g1": ModelElement(id="g1", name="Cost Goal", type="goal"),
        },
        relationships={
            "r1": ModelRelationship(id="r1", source="bs1", target="ba1", type="serving"),
            "r2": ModelRelationship(id="r2", source="bp1", target="bs1", type="flow"),
            "r3": ModelRelationship(id="r3", source="as1", target="bs1", type="realization"),
            "r4": ModelRelationship(id="r4", source="g1", target="bp1", type="influence"),
        },
        folders={
            "f1": ModelFolder(id="f1", name="Business", kind="business",
                              element_ids=["ba1", "ba2", "bs1", "bp1"]),
            "f2": ModelFolder(id="f2", name="Application", kind="application",
                              element_ids=["as1"]),
            "f3": ModelFolder(id="f3", name="Strategy", kind="strategy",
                              element_ids=["g1"]),
        },
    )
    return model


@pytest.fixture()
def service() -> SearchService:
    return SearchService(max_results=500, max_depth=5, max_nodes=100)


@pytest.fixture()
def model() -> Model:
    return _big_model()


def test_search_by_text(service, model):
    """Free text matches name (ranked) plus type/stereotype."""
    page = service.search(model, query="order")
    ids = [e.id for e in page.items]
    assert "bs1" in ids and "bp1" in ids and "as1" in ids
    assert page.total >= 3
    # Prefix match ranks above substring match.
    page2 = service.search(model, query="Customer")
    assert page2.items[0].id == "ba1"


def test_search_filters_combination(service, model):
    """Filters are AND-combined."""
    page = service.search(model, query="order", types=["business-actor"])
    assert page.total == 1
    assert page.items[0].id == "ba2"
    page = service.search(model, stereotypes=["External"])
    assert page.total == 1
    assert page.items[0].id == "ba1"
    page = service.search(model, folder_id="f2")
    assert page.total == 1
    assert page.items[0].id == "as1"


def test_search_property_filter(service, model):
    """property_key / property_value filter extended properties."""
    model.elements["ba1"].properties["channel"] = "web"
    page = service.search(model, property_key="channel", property_value="WEB")
    assert page.total == 1
    assert page.items[0].id == "ba1"


def test_search_pagination(service, model):
    """limit/offset paginate the ranked results."""
    page_all = service.search(model, limit=100)
    page = service.search(model, limit=2, offset=0)
    assert page.limit == 2 and len(page.items) == 2
    page2 = service.search(model, limit=2, offset=2)
    assert len(page2.items) == 2
    combined = [e.id for e in page.items] + [e.id for e in page2.items]
    assert len(set(combined)) == 4
    assert page_all.total == len(model.elements)


def test_neighbors_out_in_both(service, model):
    """neighbors() honors direction and depth."""
    out = service.neighbors(model, "bs1", direction="out")
    assert {n.id for n in out.nodes} == {"bs1", "ba1"}  # bs1 -> ba1
    inn = service.neighbors(model, "bs1", direction="in")
    assert {n.id for n in inn.nodes} == {"bs1", "bp1", "as1"}
    both = service.neighbors(model, "bs1", direction="both", depth=2)
    assert "g1" in {n.id for n in both.nodes}  # bs1 -> bp1 -> g1 (influence)


def test_neighbors_depth_capped(service):
    """Depth beyond the configured maximum is capped, not an error."""
    model = _big_model()
    payload = service.neighbors(model, "bs1", direction="both", depth=99)
    assert payload is not None


def test_neighbors_missing_root_raises(service, model):
    """An unknown root element raises ModelNotFoundError."""
    with pytest.raises(ModelNotFoundError):
        service.neighbors(model, "nope")


def test_folder_graph(service, model):
    """folder_graph() returns exactly the folder's subgraph."""
    payload = service.folder_graph(model, "f1")
    assert {n.id for n in payload.nodes} == {"ba1", "ba2", "bs1", "bp1"}
    # r2 (bp1 -> bs1) is inside the folder; r1 too; r3 crosses to f2.
    assert {e.id for e in payload.edges} == {"r1", "r2"}


def test_model_graph_whole(service, model):
    """model_graph() returns everything when below the node limit."""
    payload = service.model_graph(model)
    assert len(payload.nodes) == len(model.elements)
    assert len(payload.edges) == len(model.relationships)


def test_model_graph_too_large_raises(service):
    """Whole-model graphs above the node limit raise GraphTooLargeError."""
    small = SearchService(max_results=10, max_depth=2, max_nodes=5)
    with pytest.raises(GraphTooLargeError):
        small.model_graph(_big_model())


def test_model_graph_type_filter(service, model):
    """Whole-model graphs can be filtered by element type."""
    payload = service.model_graph(model, element_types=["business-actor"])
    assert {n.type for n in payload.nodes} == {"business-actor"}
    assert len(payload.nodes) == 2
