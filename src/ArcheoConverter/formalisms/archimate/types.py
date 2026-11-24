"""ArchiMate element & relationship type catalogs (3.2 and 4.0).

The catalogs map the XML local names used by the *ArchiMate Model Exchange
File Format* (the ``<archimate:businessActor>`` style tags) to **canonical
internal type names** (kebab-case) and provide display names, the
perspective/layer a concept belongs to, and the formalism versions in which
the concept is defined.

* **3.2** contains the full ArchiMate 3.x metamodel (motivation, business,
  application, technology, physical, implementation & migration layers plus
  the extension concept).
* **4.0** is 3.2 plus the new 4.0 concepts (notably the abstract
  ``resource`` concept); concepts that changed between versions are bridged
  by the migration tables in
  :mod:`ArcheoConverter.services.converter`.

The catalogs are data (not code) on purpose: they are the single source of
truth shared by the parser, the exporter, the summarizer and the
conversion engine.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ElementTypeInfo:
    """Metadata of one ArchiMate element type."""

    canonical: str  # internal kebab-case name, e.g. "business-actor"
    xml_name: str  # Model Exchange tag local name, e.g. "businessActor"
    display: str  # human readable name, e.g. "Business Actor"
    perspective: str  # layer/perspective, e.g. "business"
    abstract: bool = False
    legacy: bool = False  # concept kept for backwards import compatibility


@dataclass(frozen=True)
class RelationshipTypeInfo:
    """Metadata of one ArchiMate relationship type."""

    canonical: str  # e.g. "serving"
    xml_name: str  # e.g. "serving"
    display: str  # e.g. "Serving"


# --------------------------------------------------------------------- #
# Element types
# --------------------------------------------------------------------- #
def _et(canonical: str, xml_name: str, display: str, perspective: str,
        abstract: bool = False, legacy: bool = False) -> ElementTypeInfo:
    return ElementTypeInfo(canonical, xml_name, display, perspective, abstract, legacy)


#: ArchiMate 3.2 element catalog (canonical name -> info).
ELEMENT_TYPES_32: dict[str, ElementTypeInfo] = {
    t.canonical: t
    for t in (
        # --- Motivation Layer ------------------------------------------------ #
        _et("stakeholder", "stakeholder", "Stakeholder", "motivation"),
        _et("driver", "driver", "Driver", "motivation"),
        _et("assessment", "assessment", "Assessment", "motivation"),
        _et("goal", "goal", "Goal", "motivation"),
        _et("outcome", "outcome", "Outcome", "motivation"),
        _et("principle", "principle", "Principle", "motivation"),
        _et("requirement", "requirement", "Requirement", "motivation"),
        _et("constraint", "constraint", "Constraint", "motivation"),
        _et("meaning", "meaning", "Meaning", "motivation"),
        _et("value", "value", "Value", "motivation"),
        # --- Strategy Layer -------------------------------------------------- #
        _et("resource", "resource", "Resource", "strategy"),
        _et("capability", "capability", "Capability", "strategy"),
        _et("value-stream", "valueStream", "Value Stream", "strategy"),
        _et("course-of-action", "CourseOfAction", "Course Of Action", "strategy"),
        # --- Business Layer -------------------------------------------------- #
        _et("business-actor", "businessActor", "Business Actor", "business"),
        _et("business-role", "businessRole", "Business Role", "business"),
        _et("business-collaboration", "businessCollaboration", "Business Collaboration", "business"),
        _et("business-interface", "businessInterface", "Business Interface", "business"),
        _et("business-process", "businessProcess", "Business Process", "business"),
        _et("business-function", "businessFunction", "Business Function", "business"),
        _et("business-interaction", "businessInteraction", "Business Interaction", "business"),
        _et("business-event", "businessEvent", "Business Event", "business"),
        _et("business-service", "businessService", "Business Service", "business"),
        _et("business-object", "businessObject", "Business Object", "business"),
        _et("contract", "contract", "Contract", "business"),
        _et("representation", "representation", "Representation", "business"),
        _et("product", "product", "Product", "business"),
        # --- Application Layer ----------------------------------------------- #
        _et("application-component", "applicationComponent", "Application Component", "application"),
        _et("application-collaboration", "applicationCollaboration", "Application Collaboration", "application"),
        _et("application-interface", "applicationInterface", "Application Interface", "application"),
        _et("application-function", "applicationFunction", "Application Function", "application"),
        _et("application-interaction", "applicationInteraction", "Application Interaction", "application"),
        _et("application-process", "applicationProcess", "Application Process", "application"),
        _et("application-event", "applicationEvent", "Application Event", "application"),
        _et("application-service", "applicationService", "Application Service", "application"),
        _et("data-object", "dataObject", "Data Object", "application"),
        # --- Technology Layer ------------------------------------------------- #
        _et("node", "node", "Node", "technology"),
        _et("device", "device", "Device", "technology"),
        _et("system-software", "systemSoftware", "System Software", "technology"),
        _et("technology-collaboration", "technologyCollaboration", "Technology Collaboration", "technology"),
        _et("technology-interface", "technologyInterface", "Technology Interface", "technology"),
        _et("path", "path", "Path", "technology"),
        _et("communication-network", "communicationNetwork", "Communication Network", "technology"),
        _et("technology-function", "technologyFunction", "Technology Function", "technology"),
        _et("technology-process", "technologyProcess", "Technology Process", "technology"),
        _et("technology-interaction", "technologyInteraction", "Technology Interaction", "technology"),
        _et("technology-event", "technologyEvent", "Technology Event", "technology"),
        _et("technology-service", "technologyService", "Technology Service", "technology"),
        _et("artifact", "artifact", "Artifact", "technology"),
        _et("equipment", "equipment", "Equipment", "technology"),
        _et("facility", "facility", "Facility", "technology"),
        _et("distribution-network", "distributionNetwork", "Distribution Network", "technology"),
        _et("material", "material", "Material", "technology"),
        # --- Implementation & Migration Layer -------------------------------- #
        _et("work-package", "workPackage", "Work Package", "implementation"),
        _et("deliverable", "deliverable", "Deliverable", "implementation"),
        _et("implementation-event", "implementationEvent", "Implementation Event", "implementation"),
        _et("plateau", "plateau", "Plateau", "implementation"),
        _et("gap", "gap", "Gap", "implementation"),
        # --- Composite -------------------------------------------------- #
        _et("grouping", "grouping", "Grouping", "composite"),
        _et("location", "location", "location", "location"),
    )
}

#: ArchiMate 4.0 element catalog: majority of 3.2 elements, some renamed and some deleted, plus the 4.0-specific concepts.
ELEMENT_TYPES_40: dict[str, ElementTypeInfo] = {
    t.canonical: t
    for t in (
        # --- Motivation Domain ------------------------------------------------ #
        _et("stakeholder", "stakeholder", "Stakeholder", "motivation"),
        _et("driver", "driver", "Driver", "motivation"),
        _et("assessment", "assessment", "Assessment", "motivation"),
        _et("goal", "goal", "Goal", "motivation"),
        _et("outcome", "outcome", "Outcome", "motivation"),
        _et("principle", "principle", "Principle", "motivation"),
        _et("requirement", "requirement", "Requirement", "motivation"),
        ### DELETED: _et("constraint", "constraint", "Constraint", "motivation"),
        _et("meaning", "meaning", "Meaning", "motivation"),
        _et("value", "value", "Value", "motivation"),
        # --- Strategy Domain -------------------------------------------------- #
        _et("resource", "resource", "Resource", "strategy"),
        _et("capability", "capability", "Capability", "strategy"),
        _et("value-stream", "valueStream", "Value Stream", "strategy"),
        _et("course-of-action", "CourseOfAction", "Course Of Action", "strategy"),
        # --- Common Domain -------------------------------------------------- #
        _et("role", "role", "Role", "common"),
        _et("collaboration", "collaboration", "Collaboration", "common"),
        _et("process", "process", "Process", "common"),
        _et("function", "function", "Function", "common"),
        _et("event", "event", "Event", "common"),
        _et("service", "service", "Service", "common"),
        # --- Business Domain -------------------------------------------------- #
        _et("business-actor", "businessActor", "Business Actor", "business"),
        ### POOLING: _et("business-role", "businessRole", "Business Role", "business"),
        ### POOLING: _et("business-collaboration", "businessCollaboration", "Business Collaboration", "business"),
        _et("business-interface", "businessInterface", "Business Interface", "business"),
        ### POOLING: _et("business-process", "businessProcess", "Business Process", "business"),
        ### POOLING: _et("business-function", "businessFunction", "Business Function", "business"),
        ### DELETED: _et("business-interaction", "businessInteraction", "Business Interaction", "business"),
        ### POOLING: _et("business-event", "businessEvent", "Business Event", "business"),
        ### POOLING: _et("business-service", "businessService", "Business Service", "business"),
        _et("business-object", "businessObject", "Business Object", "business"),
        ### DELETED: _et("contract", "contract", "Contract", "business"),
        ### DELETED: _et("representation", "representation", "Representation", "business"),
        _et("product", "product", "Product", "business"),
        # --- Application Domain ----------------------------------------------- #
        _et("application-component", "applicationComponent", "Application Component", "application"),
        ### POOLING: _et("application-collaboration", "applicationCollaboration", "Application Collaboration", "application"),
        _et("application-interface", "applicationInterface", "Application Interface", "application"),
        ### POOLING: _et("application-function", "applicationFunction", "Application Function", "application"),
        ### DELETED: _et("application-interaction", "applicationInteraction", "Application Interaction", "application"),
        ### POOLING: _et("application-process", "applicationProcess", "Application Process", "application"),
        ### POOLING: _et("application-event", "applicationEvent", "Application Event", "application"),
        ### POOLING: _et("application-service", "applicationService", "Application Service", "application"),
        _et("data-object", "dataObject", "Data Object", "application"),
        # --- Technology Domain ------------------------------------------------- #
        _et("node", "node", "Node", "technology"),
        _et("device", "device", "Device", "technology"),
        _et("system-software", "systemSoftware", "System Software", "technology"),
        ### POOLING: _et("technology-collaboration", "technologyCollaboration", "Technology Collaboration", "technology"),
        _et("technology-interface", "technologyInterface", "Technology Interface", "technology"),
        _et("path", "path", "Path", "technology"),
        _et("communication-network", "communicationNetwork", "Communication Network", "technology"),
        ### POOLING: _et("technology-function", "technologyFunction", "Technology Function", "technology"),
        ### POOLING: _et("technology-process", "technologyProcess", "Technology Process", "technology"),
        ### DELETED: _et("technology-interaction", "technologyInteraction", "Technology Interaction", "technology"),
        ### POOLING: _et("technology-event", "technologyEvent", "Technology Event", "technology"),
        ### POOLING: _et("technology-service", "technologyService", "Technology Service", "technology"),
        _et("artifact", "artifact", "Artifact", "technology"),
        _et("equipment", "equipment", "Equipment", "technology"),
        _et("facility", "facility", "Facility", "technology"),
        _et("distribution-network", "distributionNetwork", "Distribution Network", "technology"),
        _et("material", "material", "Material", "technology"),
        # --- Implementation & Migration Domain -------------------------------- #
        _et("work-package", "workPackage", "Work Package", "implementation"),
        _et("deliverable", "deliverable", "Deliverable", "implementation"),
        ### DELETED: _et("implementation-event", "implementationEvent", "Implementation Event", "implementation"),
        _et("plateau", "plateau", "Plateau", "implementation"),
        ### DELETED: _et("gap", "gap", "Gap", "implementation"),
        # --- Composite -------------------------------------------------- #
        _et("grouping", "grouping", "Grouping", "composite"),
        _et("location", "location", "location", "location"),
        # --- New in 4.0 -------------------------------------------------- #
        # The abstract Resource concept introduced by ArchiMate 4.0 (technology
        # perspective). It generalizes artifacts, devices, nodes, etc.
        _et("resource", "resource", "Resource", "technology", abstract=True),
    )
}

#: Known ArchiMate folder ``type`` attribute values.
FOLDER_KINDS: tuple[str, ...] = (
    "strategy", "business", "application", "technology",
    "physical", "implementation", "motivation", "extensions", "other",
)


# --------------------------------------------------------------------- #
# Relationship types
# --------------------------------------------------------------------- #
def _rt(canonical: str, display: str) -> RelationshipTypeInfo:
    return RelationshipTypeInfo(canonical, canonical, display)


#: ArchiMate 3.2 relationship catalog (canonical name -> info).
RELATIONSHIP_TYPES_32: dict[str, RelationshipTypeInfo] = {
    t.canonical: t
    for t in (
        _rt("assignment", "Assignment"),
        _rt("aggregation", "Aggregation"),
        _rt("association", "Association"),
        _rt("composition", "Composition"),
        _rt("specialization", "Specialization"),
        _rt("serving", "Serving"),
        _rt("realization", "Realization"),
        _rt("triggering", "Triggering"),
        _rt("flow", "Flow"),
        _rt("storing", "Storing"),
        _rt("accessing", "Accessing"),
        _rt("influence", "Influence"),
        _rt("usage", "Usage"),
    )
}

#: ArchiMate 4.0 relationship catalog (same set; 4.0 does not remove any).
RELATIONSHIP_TYPES_40: dict[str, RelationshipTypeInfo] = dict(RELATIONSHIP_TYPES_32)


# --------------------------------------------------------------------- #
# Versioned lookups
# --------------------------------------------------------------------- #
def element_catalog(version: str) -> dict[str, ElementTypeInfo]:
    """Return the element catalog for a formalism version."""
    if version.startswith("4"):
        return ELEMENT_TYPES_40
    return ELEMENT_TYPES_32


def relationship_catalog(version: str) -> dict[str, RelationshipTypeInfo]:
    """Return the relationship catalog for a formalism version."""
    if version.startswith("4"):
        return RELATIONSHIP_TYPES_40
    return RELATIONSHIP_TYPES_32


def element_info(canonical: str, version: str) -> ElementTypeInfo | None:
    """Return the element type info for ``canonical`` in ``version``."""
    return element_catalog(version).get(canonical)


def canonical_from_xml(xml_name: str, version: str) -> str | None:
    """Map a Model Exchange tag local name to its canonical name."""
    for info in element_catalog(version).values():
        if info.xml_name == xml_name:
            return info.canonical
    return None


def xml_name_from_canonical(canonical: str, version: str) -> str | None:
    """Map a canonical name back to its Model Exchange tag local name."""
    info = element_info(canonical, version)
    return info.xml_name if info else None


def relationship_canonical_from_xml(xml_name: str) -> str | None:
    """Map a Model Exchange relationship tag local name to its canonical name."""
    for info in RELATIONSHIP_TYPES_32.values():
        if info.xml_name == xml_name:
            return info.canonical
    return None


def relationship_display(canonical: str) -> str:
    """Return the display name of a relationship type (unknown -> title-cased)."""
    info = RELATIONSHIP_TYPES_32.get(canonical)
    return info.display if info else canonical.replace("-", " ").title()


def element_display(canonical: str, version: str = "3.2") -> str:
    """Return the display name of an element type (unknown -> title-cased)."""
    info = element_info(canonical, version)
    return info.display if info else canonical.replace("-", " ").title()
