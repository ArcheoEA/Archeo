"""ArcheoConverter - import, convert, compare and export enterprise architecture models.

ArcheoConverter is the model engine of the Archeo project. It provides:

* in-memory storage of one or more architecture models (ArchiMate 3.2 / 4.0,
  plus BPMN 2.0, UML and SysML imports via pluggable formalism handlers);
* search, navigation and visualization of elements, relationships, views
  (folders) and folder structures;
* migration of a model from one formalism/version to another (e.g.
  ArchiMate 3.2 -> 4.0, BPMN 2 -> ArchiMate 3.2);
* comparison of two models, identification of every difference and
  generation (and application) of the integration plan that merges one
  model into the other;
* export of ArchiMate models to the OpenGroup ArchiMate Model Exchange
  XML format (full, partial or filtered);
* summarization and reporting of model characteristics and differences.

The whole engine is exposed through an OpenAPI-compatible HTTP API
(FastAPI) and a minimal browser UI served at ``/``.
"""

from __future__ import annotations

__version__ = "1.0.0"

from ArcheoConverter.core.models import (
    Formalism,
    Model,
    ModelElement,
    ModelFolder,
    ModelMetadata,
    ModelRelationship,
)
from ArcheoConverter.core.repository import ModelRepository

__all__ = [
    "__version__",
    "Formalism",
    "Model",
    "ModelElement",
    "ModelFolder",
    "ModelMetadata",
    "ModelRelationship",
    "ModelRepository",
]
