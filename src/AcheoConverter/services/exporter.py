"""Model export service (ArchiMate Model Exchange XML).

Implements the **full / partial / filtered** export scopes over a loaded
model:

* ``full``: the whole model;
* ``partial``: an explicit set of element / relationship / folder ids
  (relationships are kept only when both endpoints are selected);
* ``filtered``: declarative filters (element types, name regular
  expression, stereotypes, folders).

When the requested target version differs from the model's version, the
conversion engine is invoked first (in memory, dry run) so that the
exported file is a valid ArchiMate document for the target version.
"""

from __future__ import annotations

import logging
import re

from pydantic import BaseModel, Field

from AcheoConverter.core.models import Model
from AcheoConverter.exceptions import ExportError
from AcheoConverter.formalisms.archimate.exporter import (
    ArchiMateExporter,
    ExportResult,
    ExportSelection,
)
from AcheoConverter.services.converter import ConversionService

logger = logging.getLogger("acheoconverter.export")


class ExportRequest(BaseModel):
    """User-facing export request (API body)."""

    scope: str = "full"  # full | partial | filtered
    target_version: str | None = None  # default: the model's own version
    element_ids: list[str] = Field(default_factory=list)
    relationship_ids: list[str] = Field(default_factory=list)
    folder_ids: list[str] = Field(default_factory=list)
    element_types: list[str] = Field(default_factory=list)
    name_regex: str | None = None
    stereotypes: list[str] = Field(default_factory=list)


class ExportReport(BaseModel):
    """Report returned with an export."""

    model_id: str
    scope: str
    version: str  # the model's own version
    target_version: str  # the version of the exported document
    converted: bool = False
    element_count: int = 0
    relationship_count: int = 0
    folder_count: int = 0
    size_bytes: int = 0
    warnings: list[str] = Field(default_factory=list)


class ExportService:
    """Computes selections and delegates XML serialization to the exporter."""

    def __init__(self, converter: ConversionService, namespace: str = "") -> None:
        self._converter = converter
        self._exporter = ArchiMateExporter(namespace=namespace)

    def export(
        self,
        model: Model,
        request: ExportRequest,
    ) -> tuple[bytes, ExportReport]:
        """Export a model according to ``request``.

        Returns:
            A tuple ``(xml_bytes, report)``.

        Raises:
            ExportError: when the request is invalid or the model cannot be
                exported (non-ArchiMate model, bad regex, unknown version).
        """
        if model.metadata.formalism != "archimate":
            raise ExportError(
                f"Model '{model.model_id}' is a {model.metadata.formalism} model; "
                "XML export is only defined for ArchiMate models. Convert it "
                "to ArchiMate first.",
            )
        if request.scope not in ("full", "partial", "filtered"):
            raise ExportError(
                f"Invalid export scope '{request.scope}'.",
                details=["scopes: full, partial, filtered"],
            )

        target_version = request.target_version or (model.metadata.version or "3.2")
        if target_version not in ("3.2", "4.0"):
            raise ExportError(
                f"Unsupported target version '{target_version}'.",
                details=["supported: 3.2, 4.0"],
            )

        # Convert (in memory) when the target version differs.
        export_model = model
        converted = False
        if target_version != model.metadata.version:
            export_model, conversion_report = self._converter.convert_in_memory(
                model,
                target_formalism="archimate",
                target_version=target_version,
            )
            converted = True

        name_pattern: re.Pattern[str] | None = None
        if request.name_regex:
            try:
                name_pattern = re.compile(request.name_regex)
            except re.error as exc:
                raise ExportError(
                    f"Invalid name_regex '{request.name_regex}': {exc}"
                ) from exc

        element_ids, relationship_ids, folder_ids, warnings = self._select(
            export_model, request, name_pattern
        )
        if not element_ids:
            raise ExportError(
                "The selection is empty: nothing to export.",
                details=["check the scope, ids and filters"],
            )

        result: ExportResult = self._exporter.export(
            export_model,
            version=target_version,
            selection=ExportSelection(
                element_ids=element_ids,
                relationship_ids=relationship_ids,
                folder_ids=folder_ids,
            ),
        )
        warnings.extend(result.warnings)
        if converted:
            warnings.append(
                f"Model converted in memory from ArchiMate {model.metadata.version} "
                f"to {target_version} before export."
            )

        report = ExportReport(
            model_id=model.model_id,
            scope=request.scope,
            version=model.metadata.version,
            target_version=target_version,
            converted=converted,
            element_count=result.element_count,
            relationship_count=result.relationship_count,
            folder_count=result.folder_count,
            size_bytes=len(result.xml),
            warnings=warnings,
        )
        logger.info(
            "export complete: model=%s scope=%s target=%s elements=%d relationships=%d bytes=%d",
            model.model_id, request.scope, target_version,
            report.element_count, report.relationship_count, report.size_bytes,
        )
        return result.xml, report

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #
    def _select(
        self,
        model: Model,
        request: ExportRequest,
        name_pattern: re.Pattern[str] | None,
    ) -> tuple[set[str], set[str], set[str], list[str]]:
        """Resolve the requested scope into concrete id sets."""
        warnings: list[str] = []

        if request.scope == "full":
            elements = set(model.elements)
        elif request.scope == "partial":
            wanted = set(request.element_ids)
            for fid in request.folder_ids:
                if fid not in model.folders:
                    warnings.append(f"Unknown folder id '{fid}' in selection; ignored.")
                    continue
                elements_in_folder = self._folder_closure(model, fid)
                wanted |= elements_in_folder
            elements = {eid for eid in wanted if eid in model.elements}
            unknown = wanted - set(model.elements)
            for uid in sorted(unknown):
                warnings.append(f"Unknown element id '{uid}' in selection; ignored.")
        else:  # filtered
            elements = set()
            types_set = {t.lower() for t in request.element_types}
            stereo_set = set(request.stereotypes)
            folder_set = set(request.folder_ids)
            for eid, element in model.elements.items():
                if folder_set:
                    if element.folder_id not in folder_set:
                        continue
                if types_set and element.type.lower() not in types_set:
                    continue
                if stereo_set and not (stereo_set & set(element.stereotypes)):
                    continue
                if name_pattern is not None and not name_pattern.search(element.name):
                    continue
                elements.add(eid)

        # Relationships: explicit ids + (partial) relationships between selected elements.
        relationships: set[str] = set()
        if request.scope in ("full", "partial"):
            relationships = set(model.relationships)
        if request.relationship_ids:
            for rid in request.relationship_ids:
                if rid in model.relationships:
                    relationships.add(rid)
                else:
                    warnings.append(f"Unknown relationship id '{rid}' in selection; ignored.")
        if request.scope == "filtered":
            relationships = {
                rid for rid, rel in model.relationships.items()
                if rel.source in elements and rel.target in elements
            }

        # Folders: explicit ids, or all folders containing selected elements.
        folders: set[str]
        if request.folder_ids and request.scope in ("partial", "filtered"):
            folders = {fid for fid in request.folder_ids if fid in model.folders}
        elif request.scope == "partial":
            folders = {fid for fid in model.folders
                       if any(eid in elements for eid in model.folders[fid].element_ids)}
        else:
            folders = set(model.folders)

        return elements, relationships, folders, warnings

    @staticmethod
    def _folder_closure(model: Model, folder_id: str) -> set[str]:
        """Element ids of a folder including all nested sub-folders."""
        result: set[str] = set()
        stack = [folder_id]
        while stack:
            current = stack.pop()
            folder = model.folders.get(current)
            if folder is None:
                continue
            result.update(folder.element_ids)
            stack.extend(fid for fid, f in model.folders.items() if f.parent_id == current)
        return result


