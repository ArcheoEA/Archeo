"""Default UML -> ArchiMate conversion mapping.

Conservative defaults mapping UML constructs onto ArchiMate concepts
(see :mod:`AcheoConverter.formalisms.bpmn.mapper` for the same idea on the
BPMN side). UML packages map to folders during import; the conversion
rules only translate elements and relationships.

All tables can be overridden by registering custom conversion rules.
"""

from __future__ import annotations

#: UML element type (canonical) -> ArchiMate element type (canonical).
DEFAULT_UML_ELEMENT_MAP: dict[str, str] = {
    "class": "business-object",
    "interface": "business-service",
    "data-type": "data-object",
    "artifact": "artifact",
    "signal": "business-event",
    "information-item": "data-object",
    "use-case": "business-interaction",
    "use-case-subject": "business-actor",
    "activity": "business-process",
    "action": "business-role",
    "call-operation-action": "application-function",
    "call-behavior-action": "business-interaction",
    "decision-node": "business-event",
    "merge-node": "business-event",
    "initial-node": "business-event",
    "final-node": "business-event",
    "state-machine": "business-process",
    "state": "business-event",
    "property": "data-object",
    "attribute": "data-object",
    "operation": "application-function",
    "parameter": "data-object",
}

#: Additional stereotypes appended during conversion (type -> stereotype).
DEFAULT_UML_ELEMENT_STEREOTYPES: dict[str, str] = {
    "class": "class",
    "interface": "interface",
    "state-machine": "state-machine",
    "state": "state",
    "use-case": "use-case",
    "attribute": "attribute",
    "property": "property",
    "operation": "operation",
}

#: UML relationship type (canonical) -> ArchiMate relationship type.
DEFAULT_UML_RELATIONSHIP_MAP: dict[str, str] = {
    "association": "association",
    "aggregation": "aggregation",
    "composition": "composition",
    "generalization": "specialization",
    "dependency": "association",
    "realization": "realization",
    "object-flow": "flow",
    "control-flow": "flow",
}
