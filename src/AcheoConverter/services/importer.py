"""Model import service.

Orchestrates the full import pipeline:

1. **detect** the formalism/version when not provided explicitly;
2. **parse** the payload with the registered formalism handler;
3. **normalize** the parsed data into the canonical in-memory
   :class:`~AcheoConverter.core.models.Model` (unique ids, folder links);
4. **validate** referential integrity (dangling relationships are reported,
   not fatal);
5. **store** the model in the in-memory repository.

The service is formalism-agnostic: it only talks to the
:class:`~AcheoConverter.formalisms.registry.FormalismRegistry`.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

from AcheoConverter.core.models import Model
from AcheoConverter.core.repository import ModelRepository
from AcheoConverter.exceptions import ModelImportError
from AcheoConverter.formalisms.base import ParsedModel
from AcheoConverter.formalisms.registry import FormalismRegistry

logger = logging.getLogger("acheoconverter.importer")


class ImportResult(BaseModel):
    """Result of a successful import (returned by the API)."""

    model_id: str
    name: str
    formalism: str
    version: str
    element_count: int = 0
    relationship_count: int = 0
    folder_count: int = 0
    warnings: list[str] = Field(default_factory=list)
    skipped: list[str] = Field(default_factory=list)


class ImportService:
    """Imports model files into the in-memory repository."""

    def __init__(self, registry: FormalismRegistry, max_upload_bytes: int) -> None:
        self._registry = registry
        self._max_upload_bytes = max_upload_bytes

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def import_content(
        self,
        content: bytes,
        *,
        repository: ModelRepository,
        filename: str | None = None,
        model_id: str | None = None,
        name: str | None = None,
        formalism: str | None = None,
        version: str | None = None,
        overwrite: bool = False,
    ) -> ImportResult:
        """Import raw model content (XML bytes).

        Args:
            content: the raw file bytes.
            repository: target repository.
            filename: original file name (metadata + detection hint).
            model_id: explicit model id (generated when None).
            name: explicit model name (derived from the file name when None).
            formalism: force a formalism (auto-detected when None).
            version: force a formalism version (auto-detected when None).
            overwrite: replace an existing model with the same id.

        Raises:
            PayloadTooLargeError: when the content exceeds the size limit.
            ModelImportError: when the content cannot be parsed.
            ModelAlreadyExistsError / UnsupportedFormalismError /
            UnsupportedVersionError: as defined by the underlying layers.
        """
        from AcheoConverter.exceptions import PayloadTooLargeError

        if len(content) > self._max_upload_bytes:
            raise PayloadTooLargeError(
                f"Uploaded content is {len(content)} bytes; the limit is "
                f"{self._max_upload_bytes} bytes.",
            )
        if not content.strip():
            raise ModelImportError("The submitted content is empty.")

        if formalism is not None:
            formalism = formalism.lower()
            version = version or self._registry.default_version(formalism)
            if version is None:
                from AcheoConverter.exceptions import UnsupportedFormalismError

                raise UnsupportedFormalismError(
                    f"Unsupported formalism '{formalism}'.",
                    details=[f"supported: {', '.join(self._registry.formalisms())}"],
                )
        else:
            formalism, version = self._registry.detect(content, filename)

        handler = self._registry.handler(formalism, version)
        default_name = name or (filename.rsplit("/", 1)[-1].rsplit(".", 1)[0]
                                if filename else f"{formalism} model")
        parsed: ParsedModel = handler.parse(
            content,
            filename,
            version=version,
            name=default_name,
            model_id=model_id,
        )

        model = self._build_model(parsed, model_id=model_id, name=name or default_name)
        warnings = self._finalize(model)
        warnings.extend(parsed.warnings)

        repository.add(model, overwrite=overwrite)
        result = ImportResult(
            model_id=model.model_id,
            name=model.metadata.name,
            formalism=model.metadata.formalism,
            version=model.metadata.version,
            element_count=len(model.elements),
            relationship_count=len(model.relationships),
            folder_count=len(model.folders),
            warnings=warnings,
            skipped=parsed.skipped,
        )
        logger.info(
            "import complete: model=%s formalism=%s:%s elements=%d relationships=%d folders=%d warnings=%d",
            model.model_id, formalism, version, result.element_count,
            result.relationship_count, result.folder_count, len(warnings),
        )
        return result

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #
    @staticmethod
    def _build_model(
        parsed: ParsedModel,
        *,
        model_id: str | None,
        name: str | None,
    ) -> Model:
        """Turn parsed data into a canonical :class:`Model` with unique ids."""
        model = parsed.to_model(model_id=model_id, name=name)
        _ensure_unique_ids(model)
        return model

    @staticmethod
    def _finalize(model: Model) -> list[str]:
        """Fix folder links and report (non fatal) integrity issues."""
        warnings: list[str] = []
        # Drop folder references pointing to unknown elements (keep the model
        # navigable even with slightly inconsistent source files).
        for folder in model.folders.values():
            folder.element_ids = [eid for eid in folder.element_ids if eid in model.elements]
            folder.relationship_ids = [
                rid for rid in folder.relationship_ids if rid in model.relationships
            ]
            if folder.parent_id is not None and folder.parent_id not in model.folders:
                folder.parent_id = None
        for element in model.elements.values():
            if element.folder_id is not None and element.folder_id not in model.folders:
                element.folder_id = None
        for rel_id in model.dangling_relationship_ids():
            rel = model.relationships[rel_id]
            missing = [endpoint for endpoint in (rel.source, rel.target)
                       if endpoint not in model.elements]
            warnings.append(
                f"Relationship '{rel.id}' references missing element(s): {', '.join(missing)}."
            )
        return warnings


def _ensure_unique_ids(model: Model) -> list[str]:
    """Guarantee id uniqueness across elements, relationships and folders.

    Collisions (rare, but possible in hand-edited files) are resolved by
    suffixing the *later* occurrence (``-2``, ``-3``...) and rewriting every
    reference (relationship endpoints, folder membership, element folder
    links). Returns the list of human readable warnings.
    """
    warnings: list[str] = []
    taken: set[str] = set()

    def unique(raw: str) -> str:
        candidate = raw
        suffix = 2
        while candidate in taken:
            candidate = f"{raw}-{suffix}"
            suffix += 1
        taken.add(candidate)
        return candidate

    id_map: dict[str, str] = {}

    def dedupe(obj: Any, label: str) -> None:
        new_id = unique(obj.id)
        if new_id != obj.id:
            id_map[obj.id] = new_id
            warnings.append(f"Duplicate {label} id '{obj.id}' renamed to '{new_id}'.")
        obj.id = new_id

    for element in model.elements.values():
        dedupe(element, "element")
    for rel in model.relationships.values():
        dedupe(rel, "relationship")
    for folder in model.folders.values():
        dedupe(folder, "folder")

    if id_map:
        for rel in model.relationships.values():
            rel.source = id_map.get(rel.source, rel.source)
            rel.target = id_map.get(rel.target, rel.target)
        for folder in model.folders.values():
            folder.element_ids = [id_map.get(eid, eid) for eid in folder.element_ids]
            folder.relationship_ids = [id_map.get(rid, rid) for rid in folder.relationship_ids]
            if folder.parent_id is not None:
                folder.parent_id = id_map.get(folder.parent_id, folder.parent_id)
        for element in model.elements.values():
            if element.folder_id is not None:
                element.folder_id = id_map.get(element.folder_id, element.folder_id)
    return warnings
