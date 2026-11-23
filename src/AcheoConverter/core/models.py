"""Core, formalism-agnostic in-memory data model.

This module defines the canonical, version- and formalism-neutral
representation that every imported model is normalized into. The design is
intentionally "superset" based:

* elements, relationships and folders carry a *canonical type* string
  (e.g. ``business-actor``, ``sequence-flow``) plus a free-form
  ``properties`` dictionary that holds any formalism-specific attribute;
* the owning formalism and its version are recorded at the model level in
  :class:`ModelMetadata`, which makes it possible to keep several
  formalisms (ArchiMate, BPMN, UML, SysML) side by side in the same
  in-memory repository and to convert between them.

All structures are plain Pydantic models (an advanced typing system) so they
serialize cleanly to JSON for the API and can be validated at import time.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


def new_id(prefix: str = "id") -> str:
    """Return a new unique identifier, optionally prefixed for readability."""
    return f"{prefix}-{uuid.uuid4().hex[:16]}"


def utcnow() -> datetime:
    """Return the current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


class Formalism(str, Enum):
    """Formalisms (modeling languages) supported by the engine.

    The enum is extended through the *formalism registry* at runtime: the
    registry may register additional handlers for any of these formalisms,
    which is how the dedicated BPMN / UML / SysML extensions plug in.
    """

    ARCHIMATE = "archimate"
    BPMN = "bpmn"
    UML = "uml"
    SYSML = "sysml"
    UNKNOWN = "unknown"


class Visibility(str, Enum):
    """Visibility of an element, mirroring the ArchiMate/XMI notion."""

    PUBLIC = "public"
    PRIVATE = "private"
    PACKAGE = "package"
    INTERNAL = "internal"


class ModelElement(BaseModel):
    """A single element (object, node, event, actor...) inside a model.

    ``type`` is the *canonical* element type (kebab-case, e.g.
    ``business-actor``). The original formalism-specific tag is preserved in
    ``properties["__source_tag"]`` so conversions and exports stay reversible.
    """

    model_config = ConfigDict(extra="allow")

    id: str = Field(default_factory=lambda: new_id("el"), description="Unique element id")
    name: str = Field(default="", description="Human readable name / label")
    type: str = Field(default="unknown", description="Canonical element type (kebab-case)")
    stereotypes: list[str] = Field(default_factory=list, description="Applied stereotypes")
    description: str = Field(default="", description="Optional description / documentation")
    #: Plain string on purpose: third-party files may use non-standard
    #: visibility values; unknown values are normalized to "public".
    visibility: str = Field(default=Visibility.PUBLIC.value)
    folder_id: str | None = Field(default=None, description="Id of the containing folder/view")
    properties: dict[str, Any] = Field(default_factory=dict, description="Formalism-specific attributes")

    _KNOWN_VISIBILITY = frozenset(v.value for v in Visibility)

    @field_validator("type", "name")
    @classmethod
    def _strip(cls, value: str) -> str:
        """Normalize whitespace on name/type to keep lookups stable."""
        return value.strip() if isinstance(value, str) else value

    @field_validator("visibility", mode="before")
    @classmethod
    def _normalize_visibility(cls, value: Any) -> str:
        """Accept enums/strings; unknown values fall back to public."""
        if isinstance(value, Visibility):
            return value.value
        text = str(value or "public").lower()
        return text if text in cls._KNOWN_VISIBILITY else Visibility.PUBLIC.value


class ModelRelationship(BaseModel):
    """A directed relationship between two elements.

    ``source`` and ``target`` reference :attr:`ModelElement.id` values.
    ``aggregation`` distinguishes, for example, ArchiMate *association*
    (``aggregation=False``) from *aggregation* (``aggregation=True``).
    """

    model_config = ConfigDict(extra="allow")

    id: str = Field(default_factory=lambda: new_id("rel"), description="Unique relationship id")
    source: str = Field(description="Source element id")
    target: str = Field(description="Target element id")
    type: str = Field(default="association", description="Canonical relationship type (kebab-case)")
    aggregation: bool = Field(default=False, description="Whether the relationship is an aggregation")
    qualified_name: str | None = Field(default=None, description="Optional qualified role name")
    folder_id: str | None = Field(default=None, description="Id of the containing folder/view")
    properties: dict[str, Any] = Field(default_factory=dict, description="Formalism-specific attributes")


class ModelFolder(BaseModel):
    """A folder (or view) grouping elements and relationships.

    Folders form a tree through ``parent_id`` (``None`` for top level).
    ``kind`` records the ArchiMate folder type (``business``, ``application``,
    ``technology``...) or the equivalent grouping in other formalisms.
    """

    model_config = ConfigDict(extra="allow")

    id: str = Field(default_factory=lambda: new_id("fo"), description="Unique folder id")
    name: str = Field(default="", description="Folder / view name")
    kind: str = Field(default="other", description="Folder kind (business, application, ...)")
    parent_id: str | None = Field(default=None, description="Parent folder id (None = top level)")
    element_ids: list[str] = Field(default_factory=list, description="Ids of contained elements")
    relationship_ids: list[str] = Field(default_factory=list, description="Ids of contained relationships")
    description: str = Field(default="", description="Optional description")


class ModelMetadata(BaseModel):
    """Metadata describing a loaded model and its provenance."""

    model_id: str = Field(default_factory=lambda: new_id("model"))
    name: str = Field(default="Unnamed model")
    #: Open string on purpose: any formalism registered in the formalism
    #: registry can be stored (built-in: archimate, bpmn, uml, sysml).
    formalism: str = Field(default="unknown")
    version: str = Field(default="", description="Formalism version, e.g. '3.2' or '4.0'")
    source_file: str | None = Field(default=None, description="Origin file name (if any)")
    imported_at: datetime = Field(default_factory=utcnow)
    notes: str = Field(default="", description="Free-form notes")

    @field_validator("formalism", mode="before")
    @classmethod
    def _normalize_formalism(cls, value: Any) -> Any:
        """Normalize the formalism id (lower-case string or enum member)."""
        if isinstance(value, Formalism):
            return value.value
        if isinstance(value, str):
            return value.lower() or "unknown"
        return "unknown"


class Model(BaseModel):
    """A complete, in-memory architecture model.

    This is the primary unit stored by :class:`ModelRepository`. Elements,
    relationships and folders are kept in dictionaries keyed by id for O(1)
    access, while auxiliary indexes (by type, by folder) are computed on the
    fly by the search / navigation services to avoid stale state.
    """

    model_config = ConfigDict(extra="allow")

    metadata: ModelMetadata = Field(default_factory=ModelMetadata)
    elements: dict[str, ModelElement] = Field(default_factory=dict)
    relationships: dict[str, ModelRelationship] = Field(default_factory=dict)
    folders: dict[str, ModelFolder] = Field(default_factory=dict)

    # ------------------------------------------------------------------ #
    # Convenience accessors
    # ------------------------------------------------------------------ #
    @property
    def model_id(self) -> str:
        """Short hand for the model identifier."""
        return self.metadata.model_id

    def get_element(self, element_id: str) -> ModelElement | None:
        """Return an element by id, or ``None``."""
        return self.elements.get(element_id)

    def get_relationship(self, relationship_id: str) -> ModelRelationship | None:
        """Return a relationship by id, or ``None``."""
        return self.relationships.get(relationship_id)

    def get_folder(self, folder_id: str) -> ModelFolder | None:
        """Return a folder by id, or ``None``."""
        return self.folders.get(folder_id)

    def elements_of_type(self, element_type: str) -> list[ModelElement]:
        """Return all elements whose canonical type equals ``element_type``."""
        return [e for e in self.elements.values() if e.type == element_type]

    def relationships_of_type(self, relationship_type: str) -> list[ModelRelationship]:
        """Return all relationships whose canonical type equals ``relationship_type``."""
        return [r for r in self.relationships.values() if r.type == relationship_type]

    def element_types(self) -> dict[str, int]:
        """Return a histogram of element types (type -> count)."""
        histogram: dict[str, int] = {}
        for element in self.elements.values():
            histogram[element.type] = histogram.get(element.type, 0) + 1
        return histogram

    def relationship_types(self) -> dict[str, int]:
        """Return a histogram of relationship types (type -> count)."""
        histogram: dict[str, int] = {}
        for relationship in self.relationships.values():
            histogram[relationship.type] = histogram.get(relationship.type, 0) + 1
        return histogram

    def dangling_relationship_ids(self) -> list[str]:
        """Return ids of relationships referencing missing elements."""
        dangling: list[str] = []
        for rel in self.relationships.values():
            if rel.source not in self.elements or rel.target not in self.elements:
                dangling.append(rel.id)
        return dangling

    def summary(self) -> dict[str, Any]:
        """Return a compact summary used by list / detail API endpoints."""
        return {
            "model_id": self.model_id,
            "name": self.metadata.name,
            "formalism": self.metadata.formalism,
            "version": self.metadata.version,
            "source_file": self.metadata.source_file,
            "imported_at": self.metadata.imported_at.isoformat(),
            "element_count": len(self.elements),
            "relationship_count": len(self.relationships),
            "folder_count": len(self.folders),
            "element_types": self.element_types(),
            "relationship_types": self.relationship_types(),
        }
