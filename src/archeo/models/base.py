from pydantic import BaseModel, Field
from typing import Optional, List, Union
from enum import Enum
import uuid

class ArchiMateVersion(str, Enum):
    V3_2 = "3.2"
    V4_0 = "4.0"

class RelationshipType(str, Enum):
    COMPOSITION = "Composition"
    AGGREGATION = "Aggregation"
    ASSIGNMENT = "Assignment"
    REALIZATION = "Realization"
    SERVING = "Serving"
    ACCESS = "Access"
    INFLUENCE = "Influence"
    ASSOCIATION = "Association"
    TRIGGERING = "Triggering"
    FLOW = "Flow"
    SPECIALIZATION = "Specialization"

class BaseElement(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    documentation: Optional[str] = None
    properties: dict = {}

class Relationship(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: RelationshipType
    source: str  # Element ID
    target: str  # Element ID
