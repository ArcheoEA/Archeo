# core/model_store.py

"""
In-memory storage engine for ArchiMate models.
Uses Pydantic dataclasses and dictionary-based indexing for O(1) lookups.
"""

import uuid
from typing import Dict, List, Optional, Any, Iterator
from dataclasses import dataclass, field as dc_field
from pydantic.dataclasses import dataclass as pydantic_dataclass

from .element import ArchiElement_v32, ArchiElement_v40, ArchiElement
from .relationship import ArchiRelationship
from .folder import FolderNode

@pydantic_dataclass
class ArchiModel:
    """Container for a single ArchiMate model in memory."""
    
    # Metadata
    id: str = dc_field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    version: str  # "3.2" or "4.0"
    description: Optional[str] = None
    
    # Storage
    elements: Dict[str, ArchiElement] = dc_field(default_factory=dict)
    relationships: List[ArchiRelationship] = dc_field(default_factory=list)
    views: Dict[str, Any] = dc_field(default_factory=dict)
    folders: Dict[str, FolderNode] = dc_field(default_factory=lambda: {"root": FolderNode(name="Root")})
    
    # Indexes (for fast lookup)
    _element_id_index: Dict[str, str] = dc_field(init=False, default_factory=dict)  # id → type
    _folder_child_index: Dict[str, List[str]] = dc_field(
        init=False, default_factory=lambda: {"root": []}
    )
    
    def __post_init__(self):
        """Build indexes from stored data."""
        for eid in self.elements:
            self._element_id_index[eid] = "element"
        
        # Rebuild folder tree
        root_folder_id = "root"
        if root_folder_id not in self.folders:
            self.folders[root_folder_id] = FolderNode(name="Root", parent_id=None)
        self._rebuild_folder_tree()

    def _rebuild_folder_tree(self):
        """Reconstruct folder hierarchy index from folder nodes."""
        # Reset
        self._folder_child_index.clear()
        self._folder_child_index["root"] = []
        
        for fid, node in self.folders.items():
            if fid == "root":
                continue
            parent_id = node.parent_id or "root"
            if parent_id not in self._folder_child_index:
                self._folder_child_index[parent_id] = [fid]
            else:
                self._folder_child_index[parent_id].append(fid)

    def add_element(self, element: ArchiElement) -> str:
        """Add or replace an element. Returns its ID."""
        if element.folder_id and element.folder_id not in self.folders:
            # Auto-create folder if missing
            self.add_folder(FolderNode(id=element.folder_id, name="AutoFolder"))
        
        self.elements[element.id] = element
        return element.id

    def add_relationship(self, rel: ArchiRelationship) -> str:
        """Add a relationship. Returns its ID."""
        self.relationships.append(rel)
        return rel.id

    def get_by_id(self, eid: str) -> Optional[ArchiElement]:
        return self.elements.get(eid)

    def get_children_of_folder(self, folder_id: str) -> List[str]:
        return self._folder_child_index.get(folder_id, [])

    def add_folder(self, node: FolderNode):
        """Add a folder node."""
        self.folders[node.id] = node
        # Rebuild indexes
        if node.parent_id:
            parent_children = self._folder_child_index.setdefault(node.parent_id, [])
            if node.id not in parent_children:
                parent_children.append(node.id)
# core/model_store.py

"""
In-memory storage engine for ArchiMate models.
Uses Pydantic dataclasses and dictionary-based indexing for O(1) lookups.
"""

@pydantic_dataclass
class ArchiModel:
    """Container for a single ArchiMate model in memory."""
    
    # Metadata
    id: str = dc_field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    version: str  # "3.2" or "4.0"
    description: Optional[str] = None
    
    # Storage
    elements: Dict[str, ArchiElement] = dc_field(default_factory=dict)
    relationships: List[ArchiRelationship] = dc_field(default_factory=list)
    views: Dict[str, Any] = dc_field(default_factory=dict)
    folders: Dict[str, FolderNode] = dc_field(default_factory=lambda: {"root": FolderNode(name="Root")})
    
    # Indexes (for fast lookup)
    _element_id_index: Dict[str, str] = dc_field(init=False, default_factory=dict)  # id → type
    _folder_child_index: Dict[str, List[str]] = dc_field(
        init=False, default_factory=lambda: {"root": []}
    )
    
    def __post_init__(self):
        """Build indexes from stored data."""
        for eid in self.elements:
            self._element_id_index[eid] = "element"
        
        # Rebuild folder tree
        root_folder_id = "root"
        if root_folder_id not in self.folders:
            self.folders[root_folder_id] = FolderNode(name="Root", parent_id=None)
        self._rebuild_folder_tree()

    def _rebuild_folder_tree(self):
        """Reconstruct folder hierarchy index from folder nodes."""
        # Reset
        self._folder_child_index.clear()
        self._folder_child_index["root"] = []
        
        for fid, node in self.folders.items():
            if fid == "root":
                continue
            parent_id = node.parent_id or "root"
            if parent_id not in self._folder_child_index:
                self._folder_child_index[parent_id] = [fid]
            else:
                self._folder_child_index[parent_id].append(fid)

    def add_element(self, element: ArchiElement) -> str:
        """Add or replace an element. Returns its ID."""
        if element.folder_id and element.folder_id not in self.folders:
            # Auto-create folder if missing
            self.add_folder(FolderNode(id=element.folder_id, name="AutoFolder"))
        
        self.elements[element.id] = element
        return element.id

    def add_relationship(self, rel: ArchiRelationship) -> str:
        """Add a relationship. Returns its ID."""
        self.relationships.append(rel)
        return rel.id

    def get_by_id(self, eid: str) -> Optional[ArchiElement]:
        return self.elements.get(eid)

    def get_children_of_folder(self, folder_id: str) -> List[str]:
        return self._folder_child_index.get(folder_id, [])

    def add_folder(self, node: FolderNode):
        """Add a folder node."""
        self.folders[node.id] = node
        # Rebuild indexes
        if node.parent_id:
            parent_children = self._folder_child_index.setdefault(node.parent_id, [])
            if node.id not in parent_children:
                parent_children.append(node.id)
