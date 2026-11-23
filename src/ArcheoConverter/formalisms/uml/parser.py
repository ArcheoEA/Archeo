"""UML 2.x parser (via XMI 2.x).

Uses the shared :mod:`ArcheoConverter.formalisms.xmi` walker and turns the
flat node list into the canonical in-memory model:

* classifiers, behaviors and items become **elements** with their UML type
  (kebab-cased, e.g. ``class``, ``activity``);
* ``Package`` / ``Model`` nodes become **folders** (the model is grouped by
  its package structure);
* connectors become **relationships**:

  - ``Association`` / ``Aggregation``: endpoints resolved from the
    ``ownedEnd`` children (each referencing a classifier via ``type``);
    composite ends yield ``composition``;
  - ``Generalization``: ``general`` -> ``super``;
  - ``Dependency`` / ``Realization``: ``client`` -> ``supplier``;
  - ``ObjectFlow`` / ``ControlFlow``: ``source`` -> ``target``.

Supported XMI subset: elements with an ``xmi:id``, a ``name`` attribute,
multi references via ``xmi:references`` and single references via
attributes whose value is a known element id.
"""

from __future__ import annotations

import logging
from typing import Any

from ArcheoConverter.exceptions import ModelImportError
from ArcheoConverter.formalisms.base import FormalismHandler, ParsedModel, to_kebab
from ArcheoConverter.formalisms.xmi import (
    XmiNode,
    case_insensitive_lookup,
    package_ancestor,
    parse_xmi,
)

logger = logging.getLogger("archeoconverter.uml.parser")

#: UML node types imported as elements (type name -> display name).
UML_ELEMENT_TYPES: dict[str, str] = {
    "Class": "Class",
    "Interface": "Interface",
    "DataType": "Data Type",
    "Artifact": "Artifact",
    "Signal": "Signal",
    "InformationItem": "Information Item",
    "UseCase": "Use Case",
    "UseCaseSubject": "Use Case Subject",
    "Activity": "Activity",
    "Action": "Action",
    "CallOperationAction": "Call Operation Action",
    "CallBehaviorAction": "Call Behavior Action",
    "DecisionNode": "Decision Node",
    "MergeNode": "Merge Node",
    "InitialNode": "Initial Node",
    "FinalNode": "Final Node",
    "StateMachine": "State Machine",
    "State": "State",
    "Property": "Property",
    "Attribute": "Attribute",
    "Operation": "Operation",
    "Parameter": "Parameter",
}

#: UML node types that produce relationships (handled separately).
UML_CONNECTOR_TYPES = frozenset({
    "Association", "Aggregation", "Generalization", "Dependency",
    "Realization", "ObjectFlow", "ControlFlow", "ownedEnd", "ownedConnectionEnd",
})

#: Node types that become folders.
PACKAGE_TYPES = frozenset({"Package", "Model"})

#: XMI namespace hint used for detection.
UML_NAMESPACE_HINT = "omg.org/spec/UML"


class UmlHandler(FormalismHandler):
    """Handler for the UML formalism (via XMI)."""

    formalism = "uml"
    supported_versions = ("2.5",)
    description = "UML 2.x models exchanged as XMI"

    # ------------------------------------------------------------------ #
    # Detection
    # ------------------------------------------------------------------ #
    #: Types that are specific to UML (not shared with SysML) - used for
    #: namespace-less detection so that SysML documents are not captured.
    UML_SPECIFIC_TYPES = frozenset({
        "Class", "Interface", "Activity", "Action", "CallOperationAction",
        "ObjectFlow", "ControlFlow", "ownedEnd", "Attribute", "Operation",
        "DataType", "InformationItem", "UseCaseSubject",
    })

    def detect(self, content: bytes, filename: str | None) -> str | None:
        """Return ``"2.5"`` when the content looks like a UML XMI document."""
        try:
            nodes, _ = parse_xmi(content, context=filename or "content")
        except ModelImportError:
            return None
        if not nodes:
            return None
        if any(UML_NAMESPACE_HINT in node.namespace for node in nodes[:50]):
            return "2.5"
        # Namespace-less XMI: only accept on UML-specific types (types
        # shared with SysML, such as UseCase/StateMachine, are ambiguous).
        if any(node.namespace for node in nodes[:50]):
            return None
        if any(node.type_name in self.UML_SPECIFIC_TYPES for node in nodes[:50]):
            return "2.5"
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
        """Parse UML XMI into a :class:`ParsedModel`."""
        nodes, warnings = parse_xmi(content, context=filename or "content")
        parsed = ParsedModel(formalism="uml", version="2.5", name=name or "")
        parsed.warnings.extend(warnings)

        # Normalize type names against the known tables (case-insensitive).
        known_types = {
            **UML_ELEMENT_TYPES,
            **{t: t for t in UML_CONNECTOR_TYPES},
            **{t: t for t in PACKAGE_TYPES},
        }
        for node in nodes:
            normalized = case_insensitive_lookup(known_types, node.type_name)
            if normalized:
                node.type_name = normalized

        nodes_by_id = {node.node_id: node for node in nodes}

        # --- folders from Package/Model nodes ------------------------- #
        folders: dict[str, dict[str, Any]] = {}

        def ensure_folder(node: XmiNode) -> dict[str, Any]:
            if node.node_id not in folders:
                parent_id = package_ancestor(node, nodes_by_id, PACKAGE_TYPES)
                folders[node.node_id] = {
                    "id": node.node_id,
                    "name": node.name or node.node_id,
                    "kind": "uml-package",
                    "parent_id": parent_id,
                    "description": "",
                    "element_ids": [],
                    "relationship_ids": [],
                }
            return folders[node.node_id]

        for node in nodes:
            if node.type_name in PACKAGE_TYPES:
                ensure_folder(node)

        # --- elements --------------------------------------------------- #
        for node in nodes:
            if node.type_name not in UML_ELEMENT_TYPES:
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
                               "__source_formalism": "uml"},
            })
            if folder_id and folder_id in folders:
                folders[folder_id]["element_ids"].append(node.node_id)

        # --- relationships ---------------------------------------------- #
        for node in nodes:
            if node.type_name not in UML_CONNECTOR_TYPES:
                continue
            if node.type_name in ("ownedEnd", "ownedConnectionEnd"):
                continue  # endpoints, consumed by their parent association
            source, target, rel_type = self._connector_endpoints(node, nodes_by_id)
            if source is None or target is None:
                parsed.skipped.append(f"{node.type_name} '{node.node_id}' (missing endpoints)")
                continue
            parsed.relationships.append({
                "id": node.node_id,
                "source": source,
                "target": target,
                "type": to_kebab(rel_type),
                "aggregation": rel_type in ("Aggregation", "Composition"),
                "folder_id": package_ancestor(node, nodes_by_id, PACKAGE_TYPES),
                "properties": {"__source_tag": node.type_name,
                               "__source_formalism": "uml"},
            })

        # Attach relationship ids to the containing folder.
        for rel in parsed.relationships:
            folder_id = rel["folder_id"]
            if folder_id and folder_id in folders:
                folders[folder_id]["relationship_ids"].append(rel["id"])

        parsed.folders.extend(folders.values())
        if not parsed.elements:
            parsed.warnings.append("No UML elements found in the document.")
        logger.info(
            "uml parsed: %d elements, %d relationships, %d folders",
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
        """Resolve the (source, target, type) of a UML connector node."""
        refs = node.single_refs

        if node.type_name in ("Generalization", "Classification"):
            return refs.get("general"), refs.get("super"), node.type_name
        if node.type_name in ("Dependency", "Realization"):
            return refs.get("client"), refs.get("supplier"), node.type_name
        if node.type_name in ("ObjectFlow", "ControlFlow"):
            return refs.get("source"), refs.get("target"), node.type_name
        if node.type_name in ("Association", "Aggregation", "Composition"):
            return UmlHandler._association_endpoints(node, nodes_by_id, node.type_name)
        # Unknown connector: fall back to first two single refs.
        values = list(refs.values())
        if len(values) >= 2:
            return values[0], values[1], node.type_name
        return None, None, node.type_name

    @staticmethod
    def _association_endpoints(
        node: XmiNode,
        nodes_by_id: dict[str, XmiNode],
        declared_type: str,
    ) -> tuple[str | None, str | None, str]:
        """Resolve association endpoints from its ``ownedEnd`` children."""
        ends: list[tuple[str, bool]] = []
        for child in (n for n in nodes_by_id.values() if n.parent_id == node.node_id):
            if child.type_name not in ("ownedEnd", "ownedConnectionEnd", "Property"):
                continue
            classifier = child.single_refs.get("type")
            if classifier and classifier in nodes_by_id:
                composite = child.attrs.get("isComposite", "").lower() == "true"
                ends.append((classifier, composite))
        if len(ends) >= 2:
            source, is_composite = ends[0]
            target, _ = ends[1]
            rel_type = "Composition" if (is_composite or declared_type == "Composition") else declared_type
            return source, target, rel_type
        if len(ends) == 1:
            # Unresolved second end: use the parent package as a hint target.
            return ends[0][0], None, declared_type
        return None, None, declared_type
