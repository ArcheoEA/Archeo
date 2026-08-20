# core/relationship.py

"""
Relationship definitions for ArchiMate versions 3.2 and 4.0.
"""

from enum import Enum, auto
from typing import Optional
from dataclasses import dataclass


class RelationshipType(Enum):
    # Core relationships
    ACCESS = "Access"
    AGGREGATION = "Aggregation"
    ASSIGNMENT = "Assignment"
    AWARENESS = "Awareness"
    REALIZATION = "Realization"
    SERVING = "Serving"
    USAGE = "Usage"
    SPECIALIZATION = "Specialization"
    TRIGGERING = "Triggering"

    # ArchiMate 4.0 only
    FLOW = "Flow"


@dataclass(frozen=True)
class ArchiRelationship:
    """Represents a relationship between two elements."""
    id: str
    source_id: str
    target_id: str
    type: RelationshipType
    name: Optional[str] = None
    description: Optional[str] = None

    def __hash__(self):
        return hash(self.id)
