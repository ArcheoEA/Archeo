# tests/test_differ.py

"""
Tests for model comparison functionality.
"""

import pytest
from pathlib import Path

from ArcheoConverter.comparison.differ import ModelDiffer, ComparisonResult
from ArcheoConverter.core.model_store import ArchiModel
from ArcheoConverter.core.element import (
    ArchiElement_v32,
    ElementTypes_v32,
)


def test_model_comparison_identical(sample_xml_path):
    """Test comparing two identical models."""
    
    # Create model A
    elem1 = ArchiElement_v32(
        name="Actor",
        type=ElementTypes_v32.BusinessActor
    )
    
    model_a = ArchiModel(name="A", version="3.2")
    model_a.add_element(elem1)
    
    # Create identical model B
    elem2 = ArchiElement_v32(
        id=elem1.id,  # Same ID
        name="Actor",
        type=ElementTypes_v32.BusinessActor
    )
    
    model_b = ArchiModel(name="B", version="3.2")
    model_b.add_element(elem2)
    
    differ = ModelDiffer()
    result = differ.compare(model_a, model_b)
    
    assert isinstance(result, ComparisonResult)
    assert result.match_score > 0.95  # Should be nearly identical
    assert len(result.element_diffs) == 0


def test_model_comparison_different():
    """Test comparing different models."""
    
    elem_a = ArchiElement_v32(
        name="Actor A",
        type=ElementTypes_v32.BusinessActor
    )
    
    model_a = ArchiModel(name="A", version="3.2")
    model_a.add_element(elem_a)
    
    elem_b = ArchiElement_v32(
        name="Actor B",
        type=ElementTypes_v32.ApplicationComponent  # Different type!
    )
    
    model_b = ArchiModel(name="B", version="3.2")
    model_b.add_element(elem_b)
    
    differ = ModelDiffer()
    result = differ.compare(model_a, model_b)
    
    assert len(result.element_diffs) == 1
    diff = result.element_diffs[0]
    assert diff.type == "modified"
    assert any(c["field"] == "type" for c in diff.changes)


def test_model_comparison_missing_elements():
    """Test models with different element sets."""
    
    elem_a = ArchiElement_v32(
        name="Actor A",
        type=ElementTypes_v32.BusinessActor
    )
    
    model_a = ArchiModel(name="A", version="3.2")
    model_a.add_element(elem_a)
    
    # Model B is empty
    model_b = ArchiModel(name="B", version="3.2")
    
    differ = ModelDiffer()
    result = differ.compare(model_a, model_b)
    
    # One element should be marked as removed in B (or added in A)
    assert any(d.type == "removed" for d in result.element_diffs)
