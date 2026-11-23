"""Default SysML -> ArchiMate conversion mapping.

Conservative defaults mapping SysML constructs onto ArchiMate concepts.
All tables can be overridden by registering custom conversion rules.
"""

from __future__ import annotations

#: SysML element type (canonical) -> ArchiMate element type (canonical).
DEFAULT_SYSML_ELEMENT_MAP: dict[str, str] = {
    "block-definition": "application-component",
    "internal-block": "application-component",
    "port-definition": "application-service",
    "port": "application-service",
    "item": "data-object",
    "use-case": "business-interaction",
    "state-machine": "business-process",
    "state": "business-event",
    "constraint-block": "requirement",
    "requirement-block": "requirement",
    "constraint": "requirement",
    "action": "application-function",
}

#: Additional stereotypes appended during conversion (type -> stereotype).
DEFAULT_SYSML_ELEMENT_STEREOTYPES: dict[str, str] = {
    "block-definition": "block",
    "internal-block": "internal-block",
    "port-definition": "port",
    "port": "port",
    "constraint-block": "constraint",
    "constraint": "constraint",
    "state-machine": "state-machine",
    "state": "state",
}

#: SysML relationship type (canonical) -> ArchiMate relationship type.
DEFAULT_SYSML_RELATIONSHIP_MAP: dict[str, str] = {
    "item-flow": "flow",
    "action-flow": "flow",
    "allocation": "association",
    "classification": "specialization",
    "specialization": "specialization",
    "dependency": "association",
    "composition": "composition",
    "connector": "association",
}
