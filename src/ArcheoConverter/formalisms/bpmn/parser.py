"""BPMN 2.0 parser.

Parses BPMN 2.0 XML (``<definitions>`` root, namespace
``http://www.omg.org/spec/BPMN/20100524/MODEL`` - namespace tolerant) into
the canonical in-memory model.

Design decisions:

* elements keep their **BPMN-native canonical types** (``process``,
  ``task``, ``start-event``...): the model stays faithful to its original
  formalism; the conversion engine (rule ``bpmn-20-to-archimate-*``) later
  maps them onto ArchiMate concepts;
* one folder is created per ``process`` (its internal elements go there),
  plus ``Participants`` and ``General`` folders for pool participants and
  top-level data objects;
* ``sequenceFlow`` / ``messageFlow`` become relationships of types
  ``sequence-flow`` / ``message-flow``;
* ``dataObjectReference`` / ``dataStoreReference`` are skipped (the
  referenced objects are imported directly) and reported.
"""

from __future__ import annotations

import logging
from typing import Any

from ArcheoConverter.core.models import new_id
from ArcheoConverter.exceptions import ModelImportError
from ArcheoConverter.formalisms.base import (
    FormalismHandler,
    ParsedModel,
    attr_id,
    xml_local_name,
)

logger = logging.getLogger("archeoconverter.bpmn.parser")

#: Canonical BPMN element types (kebab-case) -> display name.
BPMN_ELEMENT_TYPES: dict[str, str] = {
    "process": "Process",
    "sub-process": "Sub Process",
    "call-activity": "Call Activity",
    "task": "Task",
    "user-task": "User Task",
    "service-task": "Service Task",
    "script-task": "Script Task",
    "manual-task": "Manual Task",
    "send-task": "Send Task",
    "receive-task": "Receive Task",
    "automatic-task": "Automatic Task",
    "business-rule-task": "Business Rule Task",
    "start-event": "Start Event",
    "end-event": "End Event",
    "intermediate-catch-event": "Intermediate Catch Event",
    "intermediate-throw-event": "Intermediate Throw Event",
    "boundary-event": "Boundary Event",
    "exclusive-gateway": "Exclusive Gateway",
    "parallel-gateway": "Parallel Gateway",
    "inclusive-gateway": "Inclusive Gateway",
    "event-based-gateway": "Event Based Gateway",
    "complex-gateway": "Complex Gateway",
    "participant": "Participant",
    "data-object": "Data Object",
    "data-store": "Data Store",
    "message": "Message",
}

#: XML local names considered elements (tag -> canonical type).
_ELEMENT_TAGS = {
    "process": "process",
    "subProcess": "sub-process",
    "callActivity": "call-activity",
    "task": "task",
    "userTask": "user-task",
    "serviceTask": "service-task",
    "scriptTask": "script-task",
    "manualTask": "manual-task",
    "sendTask": "send-task",
    "receiveTask": "receive-task",
    "automaticTask": "automatic-task",
    "businessRuleTask": "business-rule-task",
    "startEvent": "start-event",
    "endEvent": "end-event",
    "intermediateCatchEvent": "intermediate-catch-event",
    "intermediateThrowEvent": "intermediate-throw-event",
    "boundaryEvent": "boundary-event",
    "exclusiveGateway": "exclusive-gateway",
    "parallelGateway": "parallel-gateway",
    "inclusiveGateway": "inclusive-gateway",
    "eventBasedGateway": "event-based-gateway",
    "complexGateway": "complex-gateway",
    "participant": "participant",
    "dataObject": "data-object",
    "dataStore": "data-store",
    "message": "message",
}

#: XML local names that are relationships (tag -> canonical type).
_FLOW_TAGS = {
    "sequenceFlow": "sequence-flow",
    "messageFlow": "message-flow",
}

#: Tags explicitly skipped (reported in ``skipped``).
_SKIPPED_TAGS = {
    "dataObjectReference", "dataStoreReference", "textAnnotation", "artifact",
    "extensionElements", "auditing", "monitoring", "ioSpecification",
    "property", "lane", "laneSet", "participant", "bpmnElement",
}


class BpmnHandler(FormalismHandler):
    """Handler for the BPMN 2.0 formalism."""

    formalism = "bpmn"
    supported_versions = ("2.0",)
    description = "BPMN 2.0 process models"

    # ------------------------------------------------------------------ #
    # Detection
    # ------------------------------------------------------------------ #
    def detect(self, content: bytes, filename: str | None) -> str | None:
        """Return ``"2.0"`` when the content looks like a BPMN diagram."""
        try:
            root = self.parse_xml(content, context=filename or "content")
        except ModelImportError:
            return None
        if xml_local_name(root.tag) != "definitions":
            return None
        for child in root:
            if xml_local_name(child.tag) in ("process", "participant",
                                             "collaboration", "message"):
                return "2.0"
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
        """Parse BPMN 2.0 XML into a :class:`ParsedModel`."""
        root = self.parse_xml(content, context=filename or "content")
        if xml_local_name(root.tag) != "definitions":
            raise ModelImportError(
                "Not a BPMN document: the root element must be '<definitions>'."
            )

        parsed = ParsedModel(formalism="bpmn", version="2.0", name=name or "")
        folders: dict[str, dict[str, Any]] = {}

        def ensure_folder(folder_id: str, folder_name: str, kind: str) -> dict[str, Any]:
            if folder_id not in folders:
                folders[folder_id] = {
                    "id": folder_id,
                    "name": folder_name,
                    "kind": kind,
                    "parent_id": None,
                    "description": "",
                    "element_ids": [],
                    "relationship_ids": [],
                }
            return folders[folder_id]

        def add_element(elem: Any, canonical: str, folder_id: str | None) -> None:
            element_id = attr_id(elem) or new_id("bpmn")
            element = {
                "id": element_id,
                "name": (elem.get("name") or "").strip() or element_id,
                "type": canonical,
                "stereotypes": [],
                "description": "",
                "folder_id": folder_id,
                "properties": {"__source_tag": xml_local_name(elem.tag),
                               "__source_formalism": "bpmn"},
            }
            parsed.elements.append(element)
            if folder_id is not None:
                folders[folder_id]["element_ids"].append(element_id)

        def add_flow(elem: Any, canonical: str, folder_id: str | None) -> None:
            source = elem.get("sourceRef", "")
            target = elem.get("targetRef", "")
            if not source or not target:
                parsed.skipped.append(
                    f"{xml_local_name(elem.tag)} without sourceRef/targetRef"
                )
                return
            relationship_id = attr_id(elem) or new_id("flow")
            relationship = {
                "id": relationship_id,
                "source": source,
                "target": target,
                "type": canonical,
                "aggregation": False,
                "folder_id": folder_id,
                "properties": {"__source_tag": xml_local_name(elem.tag),
                               "__source_formalism": "bpmn"},
            }
            parsed.relationships.append(relationship)
            if folder_id is not None:
                folders[folder_id]["relationship_ids"].append(relationship_id)

        def walk(elem: Any, current_process: str | None) -> None:
            """Recursive walk keeping track of the enclosing process."""
            for child in elem:
                local = xml_local_name(child.tag)
                if not local:
                    continue
                if local in _ELEMENT_TAGS:
                    canonical = _ELEMENT_TAGS[local]
                    if canonical == "process":
                        process_folder_id = f"bpmn-folder-{attr_id(child) or new_id('proc')}"
                        folder = ensure_folder(
                            process_folder_id,
                            (child.get("name") or "").strip() or "BPMN Process",
                            "business",
                        )
                        add_element(child, canonical, process_folder_id)
                        # Descend into the process with it as the current scope.
                        walk(child, process_folder_id)
                    elif canonical == "participant":
                        add_element(child, canonical, "bpmn-folder-participants")
                        ensure_folder("bpmn-folder-participants", "Participants", "other")
                    else:
                        add_element(child, canonical, current_process)
                        walk(child, current_process)
                elif local in _FLOW_TAGS:
                    add_flow(child, _FLOW_TAGS[local], current_process)
                elif local in _SKIPPED_TAGS:
                    parsed.skipped.append(local)
                else:
                    # Unknown tag: descend without importing (tolerant parse).
                    walk(child, current_process)

        walk(root, None)

        # Unassigned data objects / messages (typically declared at the
        # top level of the document) are grouped in a 'General' folder.
        for element in parsed.elements:
            if element["folder_id"] is None and element["type"] in (
                "data-object", "data-store", "message"
            ):
                element["folder_id"] = "bpmn-folder-general"
                ensure_folder("bpmn-folder-general", "General", "other")[
                    "element_ids"
                ].append(element["id"])

        parsed.folders.extend(folders.values())
        if not parsed.elements:
            parsed.warnings.append("No BPMN elements found in the document.")

        logger.info(
            "bpmn parsed: %d elements, %d relationships, %d folders",
            len(parsed.elements), len(parsed.relationships), len(parsed.folders),
        )
        return parsed
