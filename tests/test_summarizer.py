"""Tests for the summarization & reporting service."""

from __future__ import annotations

from ArcheoConverter.core.models import (
    Model,
    ModelElement,
    ModelFolder,
    ModelMetadata,
    ModelRelationship,
)
from ArcheoConverter.services.comparator import ComparatorService
from ArcheoConverter.services.summarizer import SummarizerService


def _model() -> Model:
    return Model(
        metadata=ModelMetadata(model_id="m1", name="Sample", formalism="archimate",
                               version="3.2", source_file="s.archimate"),
        elements={
            "a": ModelElement(id="a", name="A", type="business-actor",
                              stereotypes=["External"]),
            "b": ModelElement(id="b", name="B", type="business-actor"),
            "c": ModelElement(id="c", name="C", type="goal"),
            "d": ModelElement(id="d", name="D", type="goal"),
        },
        relationships={
            "r1": ModelRelationship(id="r1", source="a", target="b", type="serving"),
            "r2": ModelRelationship(id="r2", source="c", target="ghost", type="influence"),
        },
        folders={
            "f1": ModelFolder(id="f1", name="Business", kind="business",
                              element_ids=["a", "b"]),
            "f2": ModelFolder(id="f2", name="Strategy", kind="strategy",
                              element_ids=["c", "d"]),
        },
    )


def test_summarize_counts_and_histograms():
    """Counts, histograms and folder stats are accurate."""
    summary = SummarizerService().summarize(_model())
    assert summary.element_count == 4
    assert summary.relationship_count == 2
    assert summary.folder_count == 2
    assert summary.elements_by_type == {"business-actor": 2, "goal": 2}
    assert summary.relationships_by_type == {"serving": 1, "influence": 1}
    assert {f.name for f in summary.folders} == {"Business", "Strategy"}
    assert summary.distinct_stereotypes == 1


def test_summarize_orphans_and_dangling():
    """Orphan elements and dangling relationships are reported."""
    summary = SummarizerService().summarize(_model())
    # Only 'd' has no relationship at all; c is an endpoint of r2 (dangling
    # but still 'involved'), a and b are endpoints of r1.
    assert summary.orphan_elements == 1
    dangling = summary.dangling_relationships
    assert len(dangling) == 1
    assert dangling[0].relationship_id == "r2"
    assert dangling[0].missing == ["ghost"]


def test_markdown_rendering():
    """The Markdown report contains the key sections."""
    model = _model()
    service = SummarizerService()
    markdown = service.render_markdown(service.summarize(model))
    assert "# Model summary - Sample" in markdown
    assert "| Formalism | archimate 3.2 |" in markdown
    assert "## Elements by type" in markdown
    assert "Business Actor" in markdown
    assert "## Dangling relationships" in markdown
    assert "r2" in markdown


def test_comparison_summary_and_markdown():
    """Comparison summaries and their Markdown rendering work."""
    service = ComparatorService()
    a = _model()
    b = a.model_copy(deep=True)
    b.elements["a"].name = "A renamed"
    b.elements["new1"] = ModelElement(id="new1", name="New", type="goal")
    del b.elements["d"]
    result = service.compare(a, b)
    summary = SummarizerService().summarize_comparison(result)
    assert summary.totals["elements_modified"] == 1
    assert summary.totals["elements_added"] == 1
    assert summary.totals["elements_removed"] == 1
    assert summary.notable
    markdown = SummarizerService().render_comparison_markdown(result)
    assert "# Comparison" in markdown
    assert "elements added" not in markdown  # table uses different labels
    assert "## Modified elements" in markdown
    assert "A renamed" in markdown
