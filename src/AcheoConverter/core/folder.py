# core/folder.py

"""
Hierarchical folder structure for organizing model elements.
"""

import uuid
from typing import List, Optional, Dict
from dataclasses import dataclass, field


@dataclass
class FolderNode:
    """Represents a node in the folder tree."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    parent_id: Optional[str] = None
    children_ids: List[str] = field(default_factory=list)
    
    def is_root(self) -> bool:
        return self.parent_id is None
    
    def add_child(self, child_id: str):
        if child_id not in self.children_ids:
            self.children_ids.append(child_id)
    
    def remove_child(self, child_id: str):
        if child_id in self.children_ids:
            self.children_ids.remove(child_id)
