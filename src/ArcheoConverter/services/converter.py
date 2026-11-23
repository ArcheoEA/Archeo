"""Model conversion (migration) engine.

Converts a loaded model from its original formalism/version to a target
formalism/version, e.g.:

* **ArchiMate 3.2 -> 4.0** (version migration): every 3.2 concept is
  preserved, 4.0-only concepts become available, and 4.0 concepts are
  down-mapped when converting back to 3.2;
* **BPMN 2.0 -> ArchiMate 3.2 / 4.0**, **UML -> ArchiMate**,
  **SysML -> ArchiMate** (cross-formalism migration) using the documented
  default mapping tables of each formalism module.

Conversions are driven by **rules** (:class:`ConversionRule`) registered in
a :class:`ConversionRuleRegistry`. Rules are plain data (element type map,
relationship type map, optional stereotype additions, fallback policies)
which makes the engine extensible: new formalism pairs can be added at
runtime or through configuration without code changes.

Unmapped constructs are handled by a per-rule **policy**:

* ``keep``: the original type is preserved (with a warning);
* ``stereotype``: the element becomes an ArchiMate ``extension`` and its
  original type is recorded as a stereotype (non-destructive);
* ``drop``: the element is removed (reported).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field

from ArcheoConverter.core.models import (
    Model,
    ModelElement,
    ModelFolder,
    ModelMetadata,
    ModelRelationship,
    new_id,
    utcnow,
)
from ArcheoConverter.core.repository import ModelRepository
from ArcheoConverter.exceptions import ConversionError
from ArcheoConverter.formalisms.archimate import types as at
from ArcheoConverter.formalisms.bpmn.mapper import (
    DEFAULT_BPMN_ELEMENT_MAP,
    DEFAULT_BPMN_ELEMENT_STEREOTYPES,
    DEFAULT_BPMN_RELATIONSHIP_MAP,
)
from ArcheoConverter.formalisms.sysml.mapper import (
    DEFAULT_SYSML_ELEMENT_MAP,
    DEFAULT_SYSML_ELEMENT_STEREOTYPES,
    DEFAULT_SYSML_RELATIONSHIP_MAP,
)
from ArcheoConverter.formalisms.uml.mapper import (
    DEFAULT_UML_ELEMENT_MAP,
    DEFAULT_UML_ELEMENT_STEREOTYPES,
    DEFAULT_UML_RELATIONSHIP_MAP,
)

logger = logging.getLogger("archeoconverter.converter")

#: Fallback element type used by the ``stereotype`` policy.
STEREOTYPE_FALLBACK_TYPE = "extension"
#: Stereotype prefix recording the original type of a stereotyped element.
ORIGINAL_TYPE_PREFIX = "original-type:"


class UnmappedItem(BaseModel):
    """One construct that had no direct mapping during conversion."""

    id: str
    name: str
    type: str
    policy: str  # keep | stereotype | drop


class ConversionReport(BaseModel):
    """Report produced by a conversion run."""

    source_model_id: str
    source_name: str
    source_formalism: str
    source_version: str
    target_formalism: str
    target_version: str
    rule_id: str
    elements_converted: int = 0
    elements_unmapped: int = 0
    relationships_converted: int = 0
    relationships_unmapped: int = 0
    folders_converted: int = 0
    unmapped_elements: list[UnmappedItem] = Field(default_factory=list)
    unmapped_relationships: list[UnmappedItem] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    duration_ms: float = 0.0


class ConversionOutcome(BaseModel):
    """Outcome of a conversion: report + (optionally) the new model id."""

    report: ConversionReport
    model_id: str | None = None  # None for dry runs


@dataclass
class ConversionRule:
    """Declarative description of one supported conversion path."""

    id: str
    source_formalism: str
    source_versions: tuple[str, ...]
    target_formalism: str
    target_versions: tuple[str, ...]
    description: str = ""
    element_map: dict[str, str] = field(default_factory=dict)
    relationship_map: dict[str, str] = field(default_factory=dict)
    element_stereotypes: dict[str, str] = field(default_factory=dict)
    element_fallback: str = "stereotype"  # keep | stereotype | drop
    relationship_fallback: str = "drop"  # drop | keep


class ConversionRuleRegistry:
    """Registry of :class:`ConversionRule` objects."""

    def __init__(self) -> None:
        self._rules: dict[str, ConversionRule] = {}

    def register(self, rule: ConversionRule) -> None:
        """Register (or replace) a conversion rule."""
        self._rules[rule.id] = rule
        logger.info(
            "conversion rule registered: %s (%s:%s -> %s:%s)",
            rule.id, rule.source_formalism, ",".join(rule.source_versions),
            rule.target_formalism, ",".join(rule.target_versions),
        )

    def all(self) -> list[ConversionRule]:
        """Return every registered rule (stable order)."""
        return [self._rules[k] for k in sorted(self._rules)]

    def find(
        self,
        source_formalism: str,
        source_version: str,
        target_formalism: str,
        target_version: str,
    ) -> ConversionRule:
        """Find the rule matching a conversion request.

        Raises:
            ConversionError: when no rule matches.
        """
        for rule in self.all():
            if (
                rule.source_formalism == source_formalism
                and source_version in rule.source_versions
                and rule.target_formalism == target_formalism
                and target_version in rule.target_versions
            ):
                return rule
        available = ", ".join(
            f"{r.id} ({r.source_formalism}:{','.join(r.source_versions)} -> "
            f"{r.target_formalism}:{','.join(r.target_versions)})"
            for r in self.all()
        ) or "none"
        raise ConversionError(
            f"No conversion rule for '{source_formalism} {source_version}' -> "
            f"'{target_formalism} {target_version}'.",
            details=[f"available rules: {available}"],
        )


class ConversionService:
    """Applies conversion rules to in-memory models."""

    def __init__(self, registry: ConversionRuleRegistry) -> None:
        self._registry = registry

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def available(self) -> list[dict[str, Any]]:
        """Public description of the available conversions (API facing)."""
        return [
            {
                "id": rule.id,
                "source_formalism": rule.source_formalism,
                "source_versions": list(rule.source_versions),
                "target_formalism": rule.target_formalism,
                "target_versions": list(rule.target_versions),
                "description": rule.description,
            }
            for rule in self._registry.all()
        ]

    def convert(
        self,
        model: Model,
        *,
        target_formalism: str,
        target_version: str,
        repository: ModelRepository,
        dry_run: bool = False,
        name: str | None = None,
        model_id: str | None = None,
        element_policy: str | None = None,
        relationship_policy: str | None = None,
    ) -> ConversionOutcome:
        """Convert ``model`` to a target formalism/version.

        Args:
            model: the source model.
            target_formalism: target formalism id (e.g. ``archimate``).
            target_version: target formalism version (e.g. ``4.0``).
            repository: repository where the new model is stored (skipped
                for dry runs).
            dry_run: when True, only the report is produced.
            name: name override for the converted model.
            model_id: id override for the converted model.
            element_policy: override the rule's element fallback policy.
            relationship_policy: override the rule's relationship policy.

        Raises:
            ConversionError: when no rule matches or policies are invalid.
        """
        source_formalism = model.metadata.formalism
        source_version = model.metadata.version or "?"
        rule = self._registry.find(source_formalism, source_version,
                                   target_formalism, target_version)

        element_policy = element_policy or rule.element_fallback
        relationship_policy = relationship_policy or rule.relationship_fallback
        if element_policy not in ("keep", "stereotype", "drop"):
            raise ConversionError(f"Invalid element policy '{element_policy}'.")
        if relationship_policy not in ("drop", "keep"):
            raise ConversionError(f"Invalid relationship policy '{relationship_policy}'.")

        return self._finish(
            model, target_formalism, target_version, repository, dry_run,
            name=name, model_id=model_id,
            element_policy=element_policy, relationship_policy=relationship_policy,
            rule=rule,
        )

    def convert_in_memory(
        self,
        model: Model,
        *,
        target_formalism: str,
        target_version: str,
        name: str | None = None,
        model_id: str | None = None,
        element_policy: str | None = None,
        relationship_policy: str | None = None,
    ) -> tuple[Model, ConversionReport]:
        """Convert a model without storing the result in any repository.

        Used by the export service to build documents for a different
        target version. Returns ``(converted_model, report)``.
        """
        source_formalism = model.metadata.formalism
        source_version = model.metadata.version or "?"
        rule = self._registry.find(source_formalism, source_version,
                                   target_formalism, target_version)
        element_policy = element_policy or rule.element_fallback
        relationship_policy = relationship_policy or rule.relationship_fallback
        new_model, report = self._do_convert(
            model, target_formalism, target_version, name=name, model_id=model_id,
            element_policy=element_policy, relationship_policy=relationship_policy,
            rule=rule,
        )
        return new_model, report

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #
    def _finish(
        self,
        model: Model,
        target_formalism: str,
        target_version: str,
        repository: ModelRepository,
        dry_run: bool,
        *,
        name: str | None,
        model_id: str | None,
        element_policy: str,
        relationship_policy: str,
        rule: ConversionRule,
    ) -> ConversionOutcome:
        new_model, report = self._do_convert(
            model, target_formalism, target_version, name=name, model_id=model_id,
            element_policy=element_policy, relationship_policy=relationship_policy,
            rule=rule,
        )
        model_id_out: str | None = None
        if not dry_run:
            repository.add(new_model)
            model_id_out = new_model.model_id
        return ConversionOutcome(report=report, model_id=model_id_out)

    def _do_convert(
        self,
        model: Model,
        target_formalism: str,
        target_version: str,
        *,
        name: str | None,
        model_id: str | None,
        element_policy: str,
        relationship_policy: str,
        rule: ConversionRule,
    ) -> tuple[Model, ConversionReport]:
        source_formalism = model.metadata.formalism
        source_version = model.metadata.version or "?"
        started = time.perf_counter()
        report = ConversionReport(
            source_model_id=model.model_id,
            source_name=model.metadata.name,
            source_formalism=source_formalism,
            source_version=source_version,
            target_formalism=target_formalism,
            target_version=target_version,
            rule_id=rule.id,
        )

        elements = self._convert_elements(model, rule, element_policy, report)
        relationships = self._convert_relationships(
            model, elements, rule, relationship_policy, report
        )
        folders = self._convert_folders(model, elements, rule, report)

        metadata = ModelMetadata(
            model_id=model_id or new_id("model"),
            name=name or f"{model.metadata.name} -> {target_formalism} {target_version}",
            formalism=target_formalism,
            version=target_version,
            source_file=model.metadata.source_file,
            imported_at=utcnow(),
            notes=(
                f"Converted from {source_formalism} {source_version} using rule "
                f"'{rule.id}'"
            ),
        )
        converted = Model(
            metadata=metadata,
            elements=elements,
            relationships=relationships,
            folders=folders,
        )
        report.duration_ms = round((time.perf_counter() - started) * 1000, 3)
        logger.info(
            "conversion %s: %s:%s -> %s:%s elements=%d/%d relationships=%d/%d",
            rule.id, source_formalism, source_version, target_formalism, target_version,
            report.elements_converted, len(model.elements),
            report.relationships_converted, len(model.relationships),
        )
        return converted, report

    @staticmethod
    def _convert_elements(
        model: Model,
        rule: ConversionRule,
        policy: str,
        report: ConversionReport,
    ) -> dict[str, ModelElement]:
        elements: dict[str, ModelElement] = {}
        for element in model.elements.values():
            target_type = rule.element_map.get(element.type)
            if target_type is None:
                report.elements_unmapped += 1
                report.unmapped_elements.append(
                    UnmappedItem(id=element.id, name=element.name,
                                 type=element.type, policy=policy)
                )
                if policy == "drop":
                    continue
                if policy == "stereotype":
                    target_type = STEREOTYPE_FALLBACK_TYPE
                    stereotypes = list(element.stereotypes) + [
                        f"{ORIGINAL_TYPE_PREFIX}{element.type}"
                    ]
                else:  # keep
                    target_type = element.type
                    stereotypes = list(element.stereotypes)
                    report.warnings.append(
                        f"Element '{element.id}' ('{element.name}') type "
                        f"'{element.type}' has no mapping; kept as-is."
                    )
            else:
                report.elements_converted += 1
                stereotypes = list(element.stereotypes)
                extra = rule.element_stereotypes.get(element.type)
                if extra and extra not in stereotypes:
                    stereotypes.append(extra)

            new_element = ModelElement(
                id=element.id,
                name=element.name,
                type=target_type,
                stereotypes=stereotypes,
                description=element.description,
                visibility=element.visibility,
                folder_id=element.folder_id,
                properties={
                    **element.properties,
                    "__converted_from": {
                        "formalism": model.metadata.formalism,
                        "version": model.metadata.version,
                        "type": element.type,
                    },
                },
            )
            elements[element.id] = new_element
        return elements

    @staticmethod
    def _convert_relationships(
        model: Model,
        elements: dict[str, ModelElement],
        rule: ConversionRule,
        policy: str,
        report: ConversionReport,
    ) -> dict[str, ModelRelationship]:
        relationships: dict[str, ModelRelationship] = {}
        for rel in model.relationships.values():
            # Endpoints of dropped elements make the relationship unusable.
            if rel.source not in elements or rel.target not in elements:
                report.relationships_unmapped += 1
                report.unmapped_relationships.append(
                    UnmappedItem(id=rel.id, name=f"{rel.source} -> {rel.target}",
                                 type=rel.type, policy="dropped-endpoint")
                )
                continue
            target_type = rule.relationship_map.get(rel.type)
            if target_type is None:
                report.relationships_unmapped += 1
                report.unmapped_relationships.append(
                    UnmappedItem(id=rel.id, name=f"{rel.source} -> {rel.target}",
                                 type=rel.type, policy=policy)
                )
                if policy == "drop":
                    continue
                target_type = rel.type
                report.warnings.append(
                    f"Relationship '{rel.id}' type '{rel.type}' has no mapping; kept as-is."
                )
            else:
                report.relationships_converted += 1
            relationships[rel.id] = ModelRelationship(
                id=rel.id,
                source=rel.source,
                target=rel.target,
                type=target_type,
                aggregation=rel.aggregation,
                qualified_name=rel.qualified_name,
                folder_id=rel.folder_id,
                properties=rel.properties,
            )
        return relationships

    @staticmethod
    def _convert_folders(
        model: Model,
        elements: dict[str, ModelElement],
        rule: ConversionRule,
        report: ConversionReport,
    ) -> dict[str, ModelFolder]:
        folders: dict[str, ModelFolder] = {}
        for folder in model.folders.values():
            kept_element_ids = [eid for eid in folder.element_ids if eid in elements]
            folders[folder.id] = ModelFolder(
                id=folder.id,
                name=folder.name,
                kind=folder.kind,
                parent_id=folder.parent_id,
                element_ids=kept_element_ids,
                relationship_ids=list(folder.relationship_ids),
                description=folder.description,
            )
            report.folders_converted += 1
        return folders


# --------------------------------------------------------------------- #
# Built-in conversion rules
# --------------------------------------------------------------------- #
def build_builtin_rules() -> list[ConversionRule]:
    """Build the built-in conversion rules shipped with the application.

    * archimate 3.2 -> 4.0  (identity for every 3.2 concept);
    * archimate 4.0 -> 3.2  (4.0-only concepts down-mapped, e.g.
      ``resource`` -> ``technology-resource``);
    * bpmn 2.0 -> archimate 3.2 / 4.0;
    * uml -> archimate 3.2 / 4.0;
    * sysml -> archimate 3.2 / 4.0.
    """
    identity_32 = {t: t for t in at.ELEMENT_TYPES_32}
    identity_40 = {t: t for t in at.ELEMENT_TYPES_40}
    rel_identity = {t: t for t in at.RELATIONSHIP_TYPES_32}

    rules: list[ConversionRule] = [
        ConversionRule(
            id="archimate-32-to-40",
            source_formalism="archimate",
            source_versions=("3.2",),
            target_formalism="archimate",
            target_versions=("4.0",),
            description="Upgrade an ArchiMate 3.2 model to ArchiMate 4.0 "
                        "(all 3.2 concepts preserved; 4.0 concepts such as "
                        "Resource become usable).",
            element_map=identity_32,
            relationship_map=rel_identity,
            element_fallback="keep",
            relationship_fallback="keep",
        ),
        ConversionRule(
            id="archimate-40-to-32",
            source_formalism="archimate",
            source_versions=("4.0",),
            target_formalism="archimate",
            target_versions=("3.2",),
            description="Downgrade an ArchiMate 4.0 model to ArchiMate 3.2 "
                        "(4.0-only concepts are mapped to their closest "
                        "3.2 equivalent, e.g. Resource -> Technology Resource).",
            element_map={**identity_40, "resource": "technology-resource"},
            relationship_map=rel_identity,
            element_fallback="stereotype",
            relationship_fallback="keep",
        ),
        ConversionRule(
            id="bpmn-20-to-archimate-32",
            source_formalism="bpmn",
            source_versions=("2.0",),
            target_formalism="archimate",
            target_versions=("3.2",),
            description="Convert a BPMN 2.0 process model into an ArchiMate "
                        "3.2 model (processes -> business processes, tasks "
                        "-> business roles, ...).",
            element_map=dict(DEFAULT_BPMN_ELEMENT_MAP),
            relationship_map=dict(DEFAULT_BPMN_RELATIONSHIP_MAP),
            element_stereotypes=dict(DEFAULT_BPMN_ELEMENT_STEREOTYPES),
            element_fallback="stereotype",
            relationship_fallback="drop",
        ),
        ConversionRule(
            id="bpmn-20-to-archimate-40",
            source_formalism="bpmn",
            source_versions=("2.0",),
            target_formalism="archimate",
            target_versions=("4.0",),
            description="Convert a BPMN 2.0 process model into an ArchiMate "
                        "4.0 model.",
            element_map=dict(DEFAULT_BPMN_ELEMENT_MAP),
            relationship_map=dict(DEFAULT_BPMN_RELATIONSHIP_MAP),
            element_stereotypes=dict(DEFAULT_BPMN_ELEMENT_STEREOTYPES),
            element_fallback="stereotype",
            relationship_fallback="drop",
        ),
        ConversionRule(
            id="uml-to-archimate-32",
            source_formalism="uml",
            source_versions=("2.5",),
            target_formalism="archimate",
            target_versions=("3.2",),
            description="Convert a UML (XMI) model into an ArchiMate 3.2 "
                        "model (classes -> business objects, interfaces -> "
                        "business services, activities -> business "
                        "processes, ...).",
            element_map=dict(DEFAULT_UML_ELEMENT_MAP),
            relationship_map=dict(DEFAULT_UML_RELATIONSHIP_MAP),
            element_stereotypes=dict(DEFAULT_UML_ELEMENT_STEREOTYPES),
            element_fallback="stereotype",
            relationship_fallback="drop",
        ),
        ConversionRule(
            id="uml-to-archimate-40",
            source_formalism="uml",
            source_versions=("2.5",),
            target_formalism="archimate",
            target_versions=("4.0",),
            description="Convert a UML (XMI) model into an ArchiMate 4.0 model.",
            element_map=dict(DEFAULT_UML_ELEMENT_MAP),
            relationship_map=dict(DEFAULT_UML_RELATIONSHIP_MAP),
            element_stereotypes=dict(DEFAULT_UML_ELEMENT_STEREOTYPES),
            element_fallback="stereotype",
            relationship_fallback="drop",
        ),
        ConversionRule(
            id="sysml-to-archimate-32",
            source_formalism="sysml",
            source_versions=("1.4",),
            target_formalism="archimate",
            target_versions=("3.2",),
            description="Convert a SysML 1.4 (XMI) model into an ArchiMate "
                        "3.2 model (blocks -> application components, "
                        "ports -> application services, ...).",
            element_map=dict(DEFAULT_SYSML_ELEMENT_MAP),
            relationship_map=dict(DEFAULT_SYSML_RELATIONSHIP_MAP),
            element_stereotypes=dict(DEFAULT_SYSML_ELEMENT_STEREOTYPES),
            element_fallback="stereotype",
            relationship_fallback="drop",
        ),
        ConversionRule(
            id="sysml-to-archimate-40",
            source_formalism="sysml",
            source_versions=("1.4",),
            target_formalism="archimate",
            target_versions=("4.0",),
            description="Convert a SysML 1.4 (XMI) model into an ArchiMate 4.0 model.",
            element_map=dict(DEFAULT_SYSML_ELEMENT_MAP),
            relationship_map=dict(DEFAULT_SYSML_RELATIONSHIP_MAP),
            element_stereotypes=dict(DEFAULT_SYSML_ELEMENT_STEREOTYPES),
            element_fallback="stereotype",
            relationship_fallback="drop",
        ),
    ]
    return rules
