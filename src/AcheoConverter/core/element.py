# core/element.py

"""
Core ArchiMate element definitions supporting versions 3.2 and 4.0.
"""

from __future__ import annotations
import uuid
from typing import Optional, Dict, List, Union, TypeVar, Generic
from enum import Enum, auto
from dataclasses import dataclass, field as dc_field
from pydantic.dataclasses import dataclass as pydantic_dataclass

T = TypeVar("T")


class ArchimateVersion(Enum):
    ARCHIMATE_32 = "3.2"
    ARCHIMATE_40 = "4.0"


class ElementTypes_v32(Enum):
    """Architect 3.2 element types."""
    # Business Layer
    BusinessActor = auto()
    BusinessRole = auto()
    BusinessCollaboration = auto()
    BusinessInterface = auto()
    BusinessProcess = auto()
    BusinessFunction = auto()
    BusinessEvent = auto()
    BusinessService = auto()
    InternalBusinessBehavior = auto()

    # Application Layer
    ApplicationComponent = auto()
    ApplicationCollaboration = auto()
    ApplicationInterface = auto()
    ApplicationFunction = auto()
    ApplicationProcess = auto()
    ApplicationEvent = auto()
    ApplicationService = auto()

    # Physical Layer
    DataObject = auto()
    Artifact = auto()
    Node = auto()
    Device = auto()
    SystemSoftware = auto()
    TechnologyService = auto()
    TechnologyFunction = auto()
    TechnologyEvent = auto()
    TechnologyInteraction = auto()
    TechnologyInterface = auto()


@pydantic_dataclass
class ArchiElement_v32:
    """Architect 3.2 element with metadata."""
    id: str = dc_field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    type: ElementTypes_v32
    documentation: Optional[str] = None
    properties: Dict[str, str] = dc_field(default_factory=dict)
    folder_id: Optional[str] = None

    def get_qualified_name(self) -> str:
        return f"{self.name} ({self.type.name})"


class ElementTypes_v40(Enum):
    """Architect 4.0 element types (includes v3.2 + new types)."""
    # All v3.2 types
    BusinessActor = auto()
    BusinessRole = auto()
    BusinessCollaboration = auto()
    BusinessInterface = auto()
    BusinessProcess = auto()
    BusinessFunction = auto()
    BusinessEvent = auto()
    BusinessService = auto()
    InternalBusinessBehavior = auto()

    ApplicationComponent = auto()
    ApplicationCollaboration = auto()
    ApplicationInterface = auto()
    ApplicationFunction = auto()
    ApplicationProcess = auto()
    ApplicationEvent = auto()
    ApplicationService = auto()

    DataObject = auto()
    Artifact = auto()
    Node = auto()
    Device = auto()
    SystemSoftware = auto()
    TechnologyService = auto()
    TechnologyFunction = auto()
    TechnologyEvent = auto()
    TechnologyInteraction = auto()
    TechnologyInterface = auto()

    # New in 4.0
    Goal = auto()
    Principle = auto()
    Requirement = auto()
    Strategy = auto()
    Resource = auto()
    Capability = auto()
    ApplicationComponent2 = auto()
    ValueStream = auto()


@pydantic_dataclass
class ArchiElement_v40(ArchiElement_v32):
    """Architect 4.0 element with additional attributes."""
    is_abstract: bool = False
    is_auditable: bool = False
    specializations: List[str] = dc_field(default_factory=list)
    patterns: List[str] = dc_field(default_factory=list)


# Type alias for unified handling
ArchiElement = Union[ArchiElement_v32, ArchiElement_v40]
