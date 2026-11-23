"""ArchiMate Model Exchange File Format exporter.

Serializes a (possibly partial) in-memory :class:`Model` back into the
standard ArchiMate Model Exchange XML format for a target version
(3.2 or 4.0). The output is compatible with mainstream ArchiMate tooling:

* ``<model>`` root carrying the XMI version and the exchange namespace;
* one ``<folder name="..." type="...">`` per folder (nested by parent),
  each holding its elements;
* one ``<xxx>`` tag per element (tag chosen from the target-version
  catalog); stereotypes / tags / properties / documentation blocks when
  present;
* one top-level relationship tag per relationship, using the
  ``aggregation="true|false"`` convention of the exchange format for the
  association / aggregation pair.

Elements that belong to no folder (or whose folder is outside the
selection) are collected in a synthetic ``Other`` folder so the file stays
well-formed for importing tools.
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any, Iterable

from AcheoConverter.core.models import Model
from AcheoConverter.exceptions import ExportError
from AcheoConverter.formalisms.archimate import types as at
from AcheoConverter.formalisms.base import xml_local_name

logger = logging.getLogger("acheoconverter.archimate.exporter")

#: Default namespace of the ArchiMate Model Exchange File Format.
DEFAULT_NAMESPACE = "http://www.archimatetool.org/archimate/types"
#: XMI namespace used for the version attribute and element identifiers.
XMI_NAMESPACE = "http://schema.omg.org/spec/XMI/2.1"


@dataclass
class ExportSelection:
    """Describes which parts of a model must be exported.

    ``None`` sets mean "everything". The export service computes these sets
    from the user request (full / partial / filtered scopes).
    """

    element_ids: set[str] | None = None
    relationship_ids: set[str] | None = None
    folder_ids: set[str] | None = None


@dataclass
class ExportResult:
    """Result of an export: the XML payload plus a small report."""

    xml: bytes
    version: str
    element_count: int
    relationship_count: int
    folder_count: int
    warnings: list[str] = field(default_factory=list)


class ArchiMateExporter:
    """Builds ArchiMate Model Exchange XML from in-memory models."""

    def __init__(self, namespace: str = DEFAULT_NAMESPACE) -> None:
        self._namespace = namespace or DEFAULT_NAMESPACE

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def export(
        self,
        model: Model,
        *,
        version: str = "3.2",
        selection: ExportSelection | None = None,
    ) -> ExportResult:
        """Export ``model`` (or the selected subset) to Model Exchange XML.

        Args:
            model: the model to export.
            version: target ArchiMate version (``"3.2"`` or ``"4.0"``);
                element tags are drawn from that version's catalog.
            selection: optional subset to export (see :class:`ExportSelection`).

        Raises:
            ExportError: on an unsupported target version.
        """
        if version not in ("3.2", "4.0"):
            raise ExportError(
                f"Unsupported ArchiMate export version '{version}'.",
                details=["supported versions: 3.2, 4.0"],
            )

        selection = selection or ExportSelection()
        warnings: list[str] = []

        element_ids = self._select(
            model.elements.keys(), selection.element_ids, warnings, "element"
        )
        relationship_ids = self._select(
            model.relationships.keys(), selection.relationship_ids, warnings, "relationship"
        )
        folder_ids = self._select(
            model.folders.keys(), selection.folder_ids, warnings, "folder"
        )

        ns = self._namespace
        root = ET.Element(f"{{{ns}}}model")
        root.set(f"{{{XMI_NAMESPACE}}}version", "2.1")

        # --- folders + elements --------------------------------------- #
        placed: set[str] = set()
        top_folders = [
            fid for fid in folder_ids
            if model.folders[fid].parent_id is None
            or model.folders[fid].parent_id not in folder_ids
        ]
        for folder_id in self._ordered_folders(model, top_folders, folder_ids):
            if not folder_has_content(model, folder_id, element_ids):
                continue
            node = self._folder_node(model.folders[folder_id])
            root.append(node)
            self._append_folder_children(
                model, node, folder_id, element_ids, version, warnings, placed
            )

        # --- synthetic folder for unassigned selected elements -------- #
        unassigned = [
            eid for eid in element_ids
            if eid not in placed
            and (
                model.elements[eid].folder_id is None
                or model.elements[eid].folder_id not in folder_ids
            )
        ]
        if unassigned:
            node = ET.Element(f"{{{ns}}}folder")
            node.set(f"{{{XMI_NAMESPACE}}}id", "unassigned-folder")
            node.set("name", "Other")
            node.set("type", "other")
            root.append(node)
            for eid in unassigned:
                node.append(self._element_node(model, eid, version, warnings))
                placed.add(eid)

        # --- relationships --------------------------------------------- #
        exported_relationships = 0
        for rid in sorted(relationship_ids, key=lambda r: model.relationships[r].id):
            rel = model.relationships[rid]
            if rel.source not in element_ids or rel.target not in element_ids:
                warnings.append(
                    f"Relationship '{rel.id}' dropped: an endpoint is outside the selection."
                )
                continue
            root.append(self._relationship_node(rel))
            exported_relationships += 1

        xml_bytes = ET.tostring(root, encoding="UTF-8", xml_declaration=True)
        folder_count = sum(
            1 for node in root.iter() if xml_local_name(node.tag) == "folder"
        )
        result = ExportResult(
            xml=xml_bytes,
            version=version,
            element_count=len(element_ids),
            relationship_count=exported_relationships,
            folder_count=folder_count,
            warnings=warnings,
        )
        logger.info(
            "archimate %s exported: %d elements, %d relationships, %d folders (%d bytes)",
            version, result.element_count, result.relationship_count,
            result.folder_count, len(xml_bytes),
        )
        return result

    # ------------------------------------------------------------------ #
    # Selection helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _select(
        available: Iterable[str],
        wanted: set[str] | None,
        warnings: list[str],
        kind: str,
    ) -> set[str]:
        """Resolve a wanted id set against what the model actually contains."""
        available_set = set(available)
        if wanted is None:
            return available_set
        result = set(wanted)
        for uid in sorted(result - available_set):
            warnings.append(f"Unknown {kind} id '{uid}' in selection; ignored.")
        return result & available_set

    @staticmethod
    def _ordered_folders(model: Model, top: list[str], folder_ids: set[str]) -> list[str]:
        """Folders in document order: parents before children (depth-first)."""
        ordered: list[str] = []
        seen: set[str] = set()

        def walk(folder_id: str) -> None:
            if folder_id in seen or folder_id not in folder_ids:
                return
            seen.add(folder_id)
            ordered.append(folder_id)
            children = [
                fid for fid in folder_ids
                if model.folders[fid].parent_id == folder_id
            ]
            for child in sorted(children, key=lambda f: model.folders[f].name.lower()):
                walk(child)

        for folder_id in sorted(top, key=lambda f: model.folders[f].name.lower()):
            walk(folder_id)
        # Orphan folders (parent outside the selection) are appended at the end.
        for fid in sorted(folder_ids - seen, key=lambda f: model.folders[f].name.lower()):
            ordered.append(fid)
        return ordered

    # ------------------------------------------------------------------ #
    # Node builders
    # ------------------------------------------------------------------ #
    def _append_folder_children(
        self,
        model: Model,
        node: ET.Element,
        folder_id: str,
        element_ids: set[str],
        version: str,
        warnings: list[str],
        placed: set[str],
    ) -> None:
        """Append the sub-folders and elements of ``folder_id`` under ``node``."""
        folder = model.folders[folder_id]
        child_ids = [
            fid for fid in model.folders
            if model.folders[fid].parent_id == folder_id
        ]
        for child_id in sorted(child_ids, key=lambda fid: model.folders[fid].name.lower()):
            if not folder_has_content(model, child_id, element_ids):
                continue
            child_node = self._folder_node(model.folders[child_id])
            node.append(child_node)
            self._append_folder_children(
                model, child_node, child_id, element_ids, version, warnings, placed
            )
        for eid in folder.element_ids:
            if eid in element_ids and model.elements[eid].folder_id == folder_id:
                node.append(self._element_node(model, eid, version, warnings))
                placed.add(eid)

    def _folder_node(self, folder: Any) -> ET.Element:
        node = ET.Element(f"{{{self._namespace}}}folder")
        node.set(f"{{{XMI_NAMESPACE}}}id", folder.id)
        node.set("name", folder.name)
        node.set("type", folder.kind or "other")
        if folder.description:
            node.set("description", folder.description)
        return node

    def _element_node(
        self,
        model: Model,
        element_id: str,
        version: str,
        warnings: list[str],
    ) -> ET.Element:
        """Build the XML node of one element, using the target-version catalog."""
        element = model.elements[element_id]
        xml_name = at.xml_name_from_canonical(element.type, version)
        if xml_name is None:
            # Type unknown in the target version: emit as extension + warning.
            xml_name = "extension"
            warnings.append(
                f"Element '{element.id}' type '{element.type}' is unknown in "
                f"ArchiMate {version}; exported as 'extension'."
            )
        node = ET.Element(f"{{{self._namespace}}}{xml_name}")
        node.set(f"{{{XMI_NAMESPACE}}}id", element.id)
        node.set("name", element.name)
        if element.visibility != "public":
            node.set("visibility", element.visibility)

        if element.stereotypes:
            stereotypes = ET.SubElement(node, f"{{{self._namespace}}}stereotypes")
            for stereotype in element.stereotypes:
                st = ET.SubElement(stereotypes, f"{{{self._namespace}}}stereotype")
                st.set("name", stereotype)
        if element.description:
            documentation = ET.SubElement(node, f"{{{self._namespace}}}documentation")
            documentation.text = element.description
        extra = {
            key: value
            for key, value in element.properties.items()
            if not key.startswith("__") and isinstance(value, (str, int, float, bool))
        }
        if extra:
            properties = ET.SubElement(node, f"{{{self._namespace}}}properties")
            for key, value in extra.items():
                prop = ET.SubElement(properties, f"{{{self._namespace}}}property")
                prop.set("key", key)
                prop.set("value", str(value))
        tags = element.properties.get("__tags")
        if tags:
            tags_node = ET.SubElement(node, f"{{{self._namespace}}}tags")
            for tag in tags:
                t = ET.SubElement(tags_node, f"{{{self._namespace}}}tag")
                t.set("name", tag)
        return node

    def _relationship_node(self, rel: Any) -> ET.Element:
        """Build the XML node of one relationship.

        The exchange format encodes the association/aggregation pair with a
        single ``aggregation`` tag plus a boolean attribute.
        """
        if rel.type in ("association", "aggregation"):
            tag = "aggregation"
            aggregation = "true" if rel.type == "aggregation" else "false"
        else:
            info = at.RELATIONSHIP_TYPES_32.get(rel.type)
            tag = info.xml_name if info else rel.type
            aggregation = None
        node = ET.Element(f"{{{self._namespace}}}{tag}")
        node.set(f"{{{XMI_NAMESPACE}}}id", rel.id)
        node.set("source", rel.source)
        node.set("target", rel.target)
        if aggregation is not None:
            node.set("aggregation", aggregation)
        if rel.qualified_name:
            node.set("qualifiedName", rel.qualified_name)
        return node


def folder_has_content(model: Model, folder_id: str, element_ids: set[str]) -> bool:
    """Return True when a folder or one of its descendants holds a selected element."""
    folder = model.folders[folder_id]
    if any(eid in element_ids for eid in folder.element_ids):
        return True
    return any(
        folder_has_content(model, child_id, element_ids)
        for child_id in model.folders
        if model.folders[child_id].parent_id == folder_id
    )


