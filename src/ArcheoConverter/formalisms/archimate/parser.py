"""ArchiMate Model Exchange File Format parser (3.2 / 4.0).

Parses the standard XML interchange format used by ArchiMate tooling
(``<archimate:model>`` root, ``<archimate:folder>`` groups, one
``<archimate:xxx>`` tag per element/relationship type) into the canonical
in-memory :class:`ParsedModel`.

Robustness rules (interoperability first):

* the parser is **namespace tolerant**: tags are matched by *local name* so
  files using any namespace URI (Archi, other vendors, custom) are accepted;
* both ``id`` and ``xmi:id`` style identifiers are accepted;
* elements may be nested inside folders (standard) or directly under the
  model root (tolerated);
* unknown element tags are **preserved** as ``extension`` elements with a
  warning (a 4.0 file parsed as 3.2 therefore keeps its 4.0 concepts);
* unknown relationship tags are preserved with their kebab-cased name and a
  warning.

The 4.0 version is auto-detected when 4.0-only tags (e.g. ``resource``)
are present.
"""

from __future__ import annotations

import logging
from typing import Any

from ArcheoConverter.core.models import new_id
from ArcheoConverter.exceptions import ModelImportError
from ArcheoConverter.formalisms.archimate import types as at
from ArcheoConverter.formalisms.base import (
    FormalismHandler,
    ParsedModel,
    attr_id,
    to_kebab,
    xml_local_name,
)

logger = logging.getLogger("archeoconverter.archimate.parser")


class ArchiMateHandler(FormalismHandler):
    """Handler for the ArchiMate formalism (versions 3.2 and 4.0)."""

    formalism = "archimate"
    supported_versions = ("3.2", "4.0")
    description = "ArchiMate (Open Group), Model Exchange File Format"

    # ------------------------------------------------------------------ #
    # Detection
    # ------------------------------------------------------------------ #
    def detect(self, content: bytes, filename: str | None) -> str | None:
        """Return ``"4.0"`` / ``"3.2"`` when the content looks ArchiMate."""
        try:
            root = self.parse_xml(content, context=filename or "content")
        except ModelImportError:
            return None
        if xml_local_name(root.tag) != "model":
            return None
        # At least one child must look like a folder or a known element.
        known_xml = {info.xml_name for info in at.ELEMENT_TYPES_40.values()}
        for child in root:
            local = xml_local_name(child.tag)
            if local == "folder" or local in known_xml:
                return self._detect_version(root)
        return None

    @staticmethod
    def _detect_version(root: Any) -> str:
        """Infer 3.2 vs 4.0 from the tags actually present.

        The presence of any 4.0-only concept (e.g. ``resource``) marks the
        file as ArchiMate 4.0; anything else is treated as 3.2.
        """
        forty_only_xml = {
            info.xml_name
            for info in at.ELEMENT_TYPES_40.values()
            if info.canonical not in at.ELEMENT_TYPES_32
        }
        for elem in root.iter():
            if xml_local_name(elem.tag) in forty_only_xml:
                return "4.0"
        return "3.2"

    # ------------------------------------------------------------------ #
    # Parsing
    # ------------------------------------------------------------------ #
    def parse(
        self,
        content: bytes,
        filename: str | None,
        *,
        version: str | None = None,
        name: str | None = None,
        model_id: str | None = None,
    ) -> ParsedModel:
        """Parse ArchiMate Model Exchange XML into a :class:`ParsedModel`."""
        root = self.parse_xml(content, context=filename or "content")
        if xml_local_name(root.tag) != "model":
            raise ModelImportError(
                "Not an ArchiMate model: the root element must be '<model>'.",
                details=[f"found root: {xml_local_name(root.tag) or '?'}"],
            )

        version = version or self._detect_version(root)
        if version not in self.supported_versions:
            raise ModelImportError(
                f"Unsupported ArchiMate version '{version}'.",
                details=[f"supported: {', '.join(self.supported_versions)}"],
            )

        parsed = ParsedModel(formalism="archimate", version=version, name=name or "")

        counter = {"element": 0, "folder": 0, "relationship": 0}
        element_catalog = at.element_catalog(version)
        xml_to_canonical = {info.xml_name: info for info in element_catalog.values()}

        # Folders (top level first, nested ones handled recursively).
        for child in root:
            local = xml_local_name(child.tag)
            if local == "folder":
                self._parse_folder(child, parsed, parent_id=None, counter=counter,
                                   xml_to_canonical=xml_to_canonical, version=version)
            else:
                # Tolerate elements/relationships placed directly under <model>.
                self._parse_content(child, parsed, folder_id=None, counter=counter,
                                    xml_to_canonical=xml_to_canonical, version=version)

        logger.info(
            "archimate %s parsed: %d elements, %d relationships, %d folders",
            version, len(parsed.elements), len(parsed.relationships), len(parsed.folders),
        )
        return parsed

    # ------------------------------------------------------------------ #
    # Internal walkers
    # ------------------------------------------------------------------ #
    def _parse_folder(
        self,
        elem: Any,
        parsed: ParsedModel,
        *,
        parent_id: str | None,
        counter: dict[str, int],
        xml_to_canonical: dict[str, at.ElementTypeInfo],
        version: str,
    ) -> None:
        """Parse one ``<folder>`` element and its (nested) content."""
        folder_id = attr_id(elem) or f"folder-{new_id('f')}"
        folder = {
            "id": folder_id,
            "name": elem.get("name", "") or folder_id,
            "kind": elem.get("type", "other") or "other",
            "parent_id": parent_id,
            "description": elem.get("description", "") or "",
            "element_ids": [],
            "relationship_ids": [],
        }
        parsed.folders.append(folder)
        counter["folder"] += 1

        for child in elem:
            local = xml_local_name(child.tag)
            if local == "folder":
                self._parse_folder(child, parsed, parent_id=folder_id, counter=counter,
                                   xml_to_canonical=xml_to_canonical, version=version)
            else:
                self._parse_content(child, parsed, folder_id=folder_id, counter=counter,
                                    xml_to_canonical=xml_to_canonical, version=version)

    def _parse_content(
        self,
        elem: Any,
        parsed: ParsedModel,
        *,
        folder_id: str | None,
        counter: dict[str, int],
        xml_to_canonical: dict[str, at.ElementTypeInfo],
        version: str,
    ) -> None:
        """Parse one element or relationship node found inside a folder/model."""
        local = xml_local_name(elem.tag)
        if not local:
            return

        # A node is a relationship when its tag is a known relationship type
        # or when it carries source/target endpoints (unknown tags are then
        # kept as relationships with a warning); anything else is an element
        # (unknown element tags are kept as 'extension' with a warning).
        rel_canonical = at.relationship_canonical_from_xml(local)
        has_endpoints = bool(elem.get("source") and elem.get("target"))
        if rel_canonical is not None or has_endpoints:
            self._parse_relationship(elem, parsed, folder_id, counter,
                                     local, rel_canonical)
            return
        self._parse_element(elem, parsed, folder_id, counter, xml_to_canonical, version)

    def _parse_element(
        self,
        elem: Any,
        parsed: ParsedModel,
        folder_id: str | None,
        counter: dict[str, int],
        xml_to_canonical: dict[str, at.ElementTypeInfo],
        version: str,
    ) -> None:
        """Parse one element node (``<archimate:businessActor>`` etc.)."""
        local = xml_local_name(elem.tag)
        info = xml_to_canonical.get(local)
        if info is None:
            # Unknown tag: keep the content, classify as extension, warn once.
            canonical = "extension"
            parsed.warnings.append(
                f"Unknown ArchiMate element tag '<{local}>' imported as 'extension'."
            )
        else:
            canonical = info.canonical
            if info.legacy:
                parsed.warnings.append(
                    f"Legacy element '<{local}>' ({info.display}) imported as '{canonical}'."
                )

        element_id = attr_id(elem) or f"elem-{new_id('e')}"
        if not attr_id(elem):
            parsed.warnings.append(f"Element '<{local}>' has no id; generated '{element_id}'.")

        element: dict[str, Any] = {
            "id": element_id,
            "name": elem.get("name", "") or element_id,
            "type": canonical,
            "stereotypes": [],
            "description": "",
            "visibility": elem.get("visibility", "public") or "public",
            "folder_id": folder_id,
            "properties": {"__source_tag": local, "__source_formalism": "archimate"},
        }

        for child in elem:
            block = xml_local_name(child.tag)
            if block == "stereotypes":
                element["stereotypes"] = [
                    (st.get("name") or "").strip()
                    for st in child
                    if xml_local_name(st.tag) == "stereotype" and (st.get("name") or "").strip()
                ]
            elif block == "tags":
                tags = [
                    (tag.get("name") or "").strip()
                    for tag in child
                    if xml_local_name(tag.tag) == "tag" and (tag.get("name") or "").strip()
                ]
                element["properties"]["__tags"] = tags
            elif block == "properties":
                for prop in child:
                    if xml_local_name(prop.tag) == "property":
                        key = prop.get("key")
                        if key:
                            element["properties"][key] = prop.get("value", "")
            elif block == "documentation":
                element["description"] = (child.text or "").strip()

        parsed.elements.append(element)
        counter["element"] += 1
        if folder_id is not None:
            folder = next((f for f in parsed.folders if f["id"] == folder_id), None)
            if folder is not None:
                folder["element_ids"].append(element_id)

    def _parse_relationship(
        self,
        elem: Any,
        parsed: ParsedModel,
        folder_id: str | None,
        counter: dict[str, int],
        local: str,
        rel_canonical: str | None,
    ) -> None:
        """Parse one relationship node (``<archimate:serving>`` etc.)."""
        if rel_canonical is None:
            # Unknown relationship tag: keep with a kebab-cased name.
            rel_canonical = to_kebab(local)
            parsed.warnings.append(
                f"Unknown ArchiMate relationship tag '<{local}>' kept as '{rel_canonical}'."
            )

        relationship_id = attr_id(elem) or f"rel-{new_id('r')}"
        source = elem.get("source", "")
        target = elem.get("target", "")
        if not source or not target:
            parsed.warnings.append(
                f"Relationship '<{local}>' is missing source/target; imported as-is."
            )

        aggregation_raw = (elem.get("aggregation") or "false").lower()
        aggregation = aggregation_raw == "true"
        # The Model Exchange format encodes Association as
        # <aggregation aggregation="false"/>.
        if local == "aggregation":
            rel_type = "aggregation" if aggregation else "association"
        else:
            rel_type = rel_canonical

        relationship: dict[str, Any] = {
            "id": relationship_id,
            "source": source,
            "target": target,
            "type": rel_type,
            "aggregation": aggregation,
            "folder_id": folder_id,
            "properties": {"__source_tag": local, "__source_formalism": "archimate"},
        }
        parsed.relationships.append(relationship)
        counter["relationship"] += 1
        if folder_id is not None:
            folder = next((f for f in parsed.folders if f["id"] == folder_id), None)
            if folder is not None:
                folder["relationship_ids"].append(relationship_id)
