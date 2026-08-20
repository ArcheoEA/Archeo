# tests/core/test_model_store.py

"""
Tests for the model storage engine.
"""

import pytest
from core.model_store import ArchiModel, FolderNode
from core.element import ArchiElement_v32, ElementTypes_v32


def test_create_empty_model():
    """Test basic model creation."""
    model = ArchiModel(
        id="test-model-1",
        name="Sample Model",
        version="4.0"
    )
    
    assert model.id == "test-model-1"
    assert model.name == "Sample Model"
    assert len(model.elements) == 0
    assert "root" in model.folders


def test_add_element():
    """Test adding and retrieving elements."""
    model = ArchiModel(id="m1", name="m1", version="3.2")
    
    element = ArchiElement_v32(
        id="e1",
        name="My Business Process",
        type=ElementTypes_v32.BusinessProcess,
        folder_id=None
    )
    
    model.add_element(element)
    
    assert len(model.elements) == 1
    assert model.get_by_id("e1") is element


def test_folder_indexing():
    """Test folder hierarchy management."""
    model = ArchiModel(id="m2", name="m2", version="3.2")
    
    root_folder = FolderNode(name="Root", parent_id=None)
    child_folder = FolderNode(name="Processes", parent_id=root_folder.id, children_ids=["e1"])
    
    model.folders[root_folder.id] = root_folder
    model.folders[child_folder.id] = child_folder
    
    # Rebuild tree index
    model._rebuild_folder_tree()
    
    assert "root" in model._folder_id_index
    assert child_folder.id in model._folder_id_index["root"]


def test_element_update():
    """Test updating an existing element."""
    model = ArchiModel(id="m3", name="m3", version="4.0")
    
    e1 = ArchiElement_v32(
        id="e1",
        name="Old Name",
        type=ElementTypes_v32.BusinessProcess
    )
    model.add_element(e1)
    
    # Update
    e1.name = "New Name"
    model.elements[e1.id] = e1
    
    assert model.get_by_id("e1").name == "New Name"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
