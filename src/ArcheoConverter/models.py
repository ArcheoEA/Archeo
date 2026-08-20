"""In-memory representation of ArchiMate models."""

from dataclasses import dataclass, field
from typing import Optional

@dataclass
class ArchiMateElement:
    id: str
    type: str
    name: str = ""
    description: str = ""
    properties: dict[str, str] = field(default_factory=dict)
    folder_id: Optional[str] = None
    view_ids: list[str] = field(default_factory=list)

@dataclass
class ArchiMateRelationship:
    id: str
    type: str
    source_id: str
    target_id: str
    properties: dict[str, str] = field(default_factory=dict)

@dataclass
class ArchiMateView:
    id: str
    name: str = ""
    element_ids: list[str] = field(default_factory=list)
    relationship_ids: list[str] = field(default_factory=list)

@dataclass
class ArchiMateModel:
    id: str
    name: str = ""
    version: str = "3.2"
    elements: dict[str, ArchiMateElement] = field(default_factory=dict)
    relationships: dict[str, ArchiMateRelationship] = field(default_factory=dict)
    views: dict[str, ArchiMateView] = field(default_factory=dict)
    folders: dict[str, str] = field(default_factory=dict)  # id -> name
    metadata: dict[str, str] = field(default_factory=dict)
