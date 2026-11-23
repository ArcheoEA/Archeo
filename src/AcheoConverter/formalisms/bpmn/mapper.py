"""Default BPMN 2.0 -> ArchiMate conversion mapping.

These tables are the **dedicated parameters** that drive the built-in
``bpmn-20-to-archimate-*`` conversion rules. They are intentionally
conservative and documented: every BPMN construct is mapped to the closest
ArchiMate 3.2/4.0 concept.

* processes map to *Business Process* (or *Application Process* for
  application-level diagrams - tune the map to your needs);
* tasks map to *Business Role* (a unit of work) - service/script tasks map
  to *Application Function* since they are typically executed by software;
* events and gateways map to *Business Event* (control-flow semantics);
* participants map to *Business Actor* (an organization performing a
  process);
* data objects / stores map to *Data Object*;
* sequence/message flows map to *Flow*.

All tables can be overridden by registering custom conversion rules
(see :mod:`AcheoConverter.services.converter`).
"""

from __future__ import annotations

#: BPMN element type (canonical) -> ArchiMate element type (canonical).
DEFAULT_BPMN_ELEMENT_MAP: dict[str, str] = {
    "process": "business-process",
    "sub-process": "business-process",
    "call-activity": "business-interaction",
    "task": "business-role",
    "user-task": "business-role",
    "service-task": "application-function",
    "script-task": "application-function",
    "manual-task": "business-role",
    "send-task": "business-event",
    "receive-task": "business-event",
    "automatic-task": "business-role",
    "business-rule-task": "business-role",
    "start-event": "business-event",
    "end-event": "business-event",
    "intermediate-catch-event": "business-event",
    "intermediate-throw-event": "business-event",
    "boundary-event": "business-event",
    "exclusive-gateway": "business-event",
    "parallel-gateway": "business-event",
    "inclusive-gateway": "business-event",
    "event-based-gateway": "business-event",
    "complex-gateway": "business-event",
    "participant": "business-actor",
    "data-object": "data-object",
    "data-store": "data-object",
    "message": "business-communication-path",
}

#: Additional stereotypes appended during conversion (type -> stereotype).
DEFAULT_BPMN_ELEMENT_STEREOTYPES: dict[str, str] = {
    "participant": "participant",
    "data-store": "data-store",
    "sub-process": "sub-process",
}

#: BPMN relationship type (canonical) -> ArchiMate relationship type.
DEFAULT_BPMN_RELATIONSHIP_MAP: dict[str, str] = {
    "sequence-flow": "flow",
    "message-flow": "flow",
}
