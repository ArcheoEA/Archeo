# tests/test_model_store.py

"""
Tests for model storage engine.
"""

import pytest
from pathlib import Path

from ArcheoConverter.core.model_store import ArchiModel, FolderNode
from ArcheoConverter.core.element import (
    ArchiElement_v32,
    ElementTypes_v32
)


def test_archimodel_initialization():
    """Test model creation."""
    model = ArchiModel(
        name="Test Model",
        version="4.0"
    )
    
    assert model.name == "Test Model"
    assert model.version == "4.0"
    assert len(model.elements) == 0
    assert "root" in model.folders


def test_add_element():
    """Test adding elements to a model."""
    model = ArchiModel(name="Test", version="3.2")
    
    elem1 = ArchiElement_v32(
        name="Actor",
        type=ElementTypes_v32.BusinessActor
    )
    
    elem_id = model.add_element(elem1)
    
    assert elem_id == elem1.id
    assert len(model.elements) == 1
    assert model.get_by_id(elem1.id) == elem1


def test_add_folder():
    """Test folder management."""
    model = ArchiModel(name="Test", version="3.2")
    
    root_node = model.folders["root"]
    assert root_node.is_root()
    
    # Add child folder
    child = FolderNode(
        name="Applications",
        parent_id="root"
    )
    model.add_folder(child)
    
    children = model.get_children_of_folder("root")
    assert child.id in children


def test_folder_index_rebuild():
    """Test that folder index is rebuilt correctly."""
    model = ArchiModel(name="Test", version="3.2")
    
    # Add folders
    f1 = FolderNode(name="Folder 1", parent_id=None)
    f2 = FolderNode(name="Folder 2", parent_id=f1.id)
    
    model.add_folder(f1)
    model.add_folder(f2)
    
    # Check hierarchy
    assert f1.id in model.get_children_of_folder("root")
    assert f2.id in model.get_children_of_folder(f1.id)
