"""SysML 1.4 parser (via XMI).

Uses the shared :mod:`AcheoConverter.formalisms.xmi` walker:

* blocks, ports, items and requirements become **elements** with their
  SysML type (kebab-cased, e.g. ``block-definition``, ``port-definition``);
* ``Package`` nodes become **folders**;
* connectors become **relationships**:

  - ``ItemFlow`` / ``ActionFlow``: ``source`` -> ``target``;
  - ``Allocation``: ``source`` -> ``target``;
  - ``Classification`` / ``Specialization``: ``general`` -> ``super``;
  - ``Dependency``: ``client`` -> ``supplier``;
  - ``Composition`` / ``Connector``: endpoints from ``source``/``target``
    or from the referenced ``part`` of owned ends.

Supported XMI subset: Eclipse SysML 1.4 style documents
(``http://www.eclipse.org/sysml/1.4``) and equivalent namespace-less
documents.
"""

from __future__ import annotations

import logging
from typing import Any

from AcheoConverter.exceptions import ModelImportError
from AcheoConverter.formalisms.base import FormalismHandler, ParsedModel, to_kebab
from AcheoConverter.formalisms.xmi import (
    XmiNode,
    case_insensitive_lookup,
    package_ancestor,
    parse_xmi,
)

logger = logging.getLogger("acheoconverter.sysml.parser")

#: SysML node types imported as elements (type name -> display name).
SYSML_ELEMENT_TYPES: dict[str, str] = {
    "BlockDefinition": "Block Definition",
    "InternalBlock": "Internal Block",
    "PortDefinition": "Port Definition",
    "Port": "Port",
    "Item": "Item",
    "UseCase": "Use Case",
    "StateMachine": "State Machine",
    "State": "State",
    "ConstraintBlock": "Constraint Block",
    "RequirementBlock": "Requirement Block",
    "Constraint": "Constraint",
    "Action": "Action",
}

#: SysML node types that produce relationships.
SYSML_CONNECTOR_TYPES = frozenset({
    "ItemFlow", "ActionFlow", "Allocation", "Classification", "Specialization",
    "Dependency", "Composition", "Connector", "ownedEnd",
})

PACKAGE_TYPES = frozenset({"Package"})

#: XMI namespace hint used for detection.
SYSML_NAMESPACE_HINTS = ("eclipse.org/sysml", "omg.org/spec/SysML")

#: Types specific to SysML - used for namespace-less detection.
SYSML_SPECIFIC_TYPES = frozenset({
    "BlockDefinition", "InternalBlock", "PortDefinition", "ConstraintBlock",
    "RequirementBlock", "ItemFlow",
})


class SysmlHandler(FormalismHandler):
    """Handler for the SysML formalism (via XMI)."""

    formalism = "sysml"
    supported_versions = ("1.4",)
    description = "SysML 1.4 models exchanged as XMI"

    # ------------------------------------------------------------------ #
    # Detection
    # ------------------------------------------------------------------ #
    def detect(self, content: bytes, filename: str | None) -> str | None:
        """Return ``"1.4"`` when the content looks like a SysML XMI document."""
        try:
            nodes, _ = parse_xmi(content, context=filename or "content")
        except ModelImportError:
            return None
        if not nodes:
            return None
        if any(
            any(hint in node.namespace for hint in SYSML_NAMESPACE_HINTS)
            for node in nodes[:50]
        ):
            return "1.4"
        # Namespace-less XMI: only accept on SysML-specific types so that
        # plain UML documents are not captured.
        if any(node.namespace for node in nodes[:50]):
            return None
        if any(node.type_name in SYSML_SPECIFIC_TYPES for node in nodes[:50]):
            return "1.4"
        return None

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
        """Parse SysML XMI into a :class:`ParsedModel`."""
        nodes, warnings = parse_xmi(content, context=filename or "content")
        parsed = ParsedModel(formalism="sysml", version="1.4", name=name or "")
        parsed.warnings.extend(warnings)

        # Normalize type names against the known tables (case-insensitive).
        known_types = {
            **SYSML_ELEMENT_TYPES,
            **{t: t for t in SYSML_CONNECTOR_TYPES},
            **{t: t for t in PACKAGE_TYPES},
        }
        for node in nodes:
            normalized = case_insensitive_lookup(known_types, node.type_name)
            if normalized:
                node.type_name = normalized

        nodes_by_id = {node.node_id: node for node in nodes}

        # --- folders from Package nodes -------------------------------- #
        folders: dict[str, dict[str, Any]] = {}

        def ensure_folder(node: XmiNode) -> dict[str, Any]:
            if node.node_id not in folders:
                parent_id = package_ancestor(node, nodes_by_id, PACKAGE_TYPES)
                folders[node.node_id] = {
                    "id": node.node_id,
                    "name": node.name or node.node_id,
                    "kind": "sysml-package",
                    "parent_id": parent_id,
                    "description": "",
                    "element_ids": [],
                    "relationship_ids": [],
                }
            return folders[node.node_id]

        for node in nodes:
            if node.type_name in PACKAGE_TYPES:
                ensure_folder(node)

        # --- elements ---------------------------------------------------- #
        for node in nodes:
            if node.type_name not in SYSML_ELEMENT_TYPES:
                continue
            folder_id = package_ancestor(node, nodes_by_id, PACKAGE_TYPES)
            parsed.elements.append({
                "id": node.node_id,
                "name": node.name or node.node_id,
                "type": to_kebab(node.type_name),
                "stereotypes": [],
                "description": "",
                "folder_id": folder_id,
                "properties": {"__source_tag": node.type_name,
                               "__source_formalism": "sysml"},
            })
            if folder_id and folder_id in folders:
                folders[folder_id]["element_ids"].append(node.node_id)

        # --- relationships ------------------------------------------------ #
        for node in nodes:
            if node.type_name in SYSML_CONNECTOR_TYPES:
                if node.type_name == "ownedEnd":
                    continue  # consumed by its parent connector
                source, target, rel_type = self._connector_endpoints(node, nodes_by_id)
                if source is None or target is None:
                    parsed.skipped.append(
                        f"{node.type_name} '{node.node_id}' (missing endpoints)"
                    )
                    continue
                parsed.relationships.append({
                    "id": node.node_id,
                    "source": source,
                    "target": target,
                    "type": to_kebab(rel_type),
                    "aggregation": rel_type == "Composition",
                    "folder_id": package_ancestor(node, nodes_by_id, PACKAGE_TYPES),
                    "properties": {"__source_tag": node.type_name,
                                   "__source_formalism": "sysml"},
                })

        for rel in parsed.relationships:
            folder_id = rel["folder_id"]
            if folder_id and folder_id in folders:
                folders[folder_id]["relationship_ids"].append(rel["id"])

        parsed.folders.extend(folders.values())
        if not parsed.elements:
            parsed.warnings.append("No SysML elements found in the document.")
        logger.info(
            "sysml parsed: %d elements, %d relationships, %d folders",
            len(parsed.elements), len(parsed.relationships), len(parsed.folders),
        )
        return parsed

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _connector_endpoints(
        node: XmiNode,
        nodes_by_id: dict[str, XmiNode],
    ) -> tuple[str | None, str | None, str]:
        """Resolve the (source, target, type) of a SysML connector node."""
        refs = node.single_refs

        if node.type_name in ("Classification", "Specialization"):
            return refs.get("general"), refs.get("super"), node.type_name
        if node.type_name == "Dependency":
            return refs.get("client"), refs.get("supplier"), node.type_name
        if node.type_name in ("ItemFlow", "ActionFlow", "Allocation"):
            return refs.get("source"), refs.get("target"), node.type_name
        if node.type_name in ("Composition", "Connector"):
            # Try direct references first, then owned-end parts.
            if refs.get("source") and refs.get("target"):
                return refs["source"], refs["target"], node.type_name
            parts: list[str] = []
            for child in (n for n in nodes_by_id.values() if n.parent_id == node.node_id):
                if child.type_name in ("ownedEnd", "ownedConnectionEnd"):
                    part = child.single_refs.get("part") or child.single_refs.get("type")
                    if part and part in nodes_by_id:
                        parts.append(part)
            if len(parts) >= 2:
                return parts[0], parts[1], node.type_name
            return (parts[0] if parts else None), (parts[1] if len(parts) > 1 else None), node.type_name
        values = list(refs.values())
        if len(values) >= 2:
            return values[0], values[1], node.type_name
        return None, None, node.type_name
