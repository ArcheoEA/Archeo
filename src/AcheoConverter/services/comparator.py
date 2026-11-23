"""Model comparison and integration planning service.

Compares two loaded models (same formalism; versions may differ, e.g.
ArchiMate 3.2 vs 4.0) and produces:

* a **comparison result**: every added / removed / modified element,
  relationship and folder, with the exact field-level differences;
* an **integration plan**: the ordered list of modifications required to
  merge one model (the *source*) into the other (the *base*) - new folders,
  new elements, element updates, new/updated relationships (and optionally
  removals);
* **plan application**: the plan can be applied to a copy of the base
  model, returning the merged model.

Matching strategies (``match_by``):

* ``id``: elements match when they share the same id;
* ``name``: elements match by (case-insensitive) name;
* ``id_then_name`` (default): id first, then name for the remainder.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

from AcheoConverter.core.models import Model, ModelElement, ModelFolder, ModelRelationship
from AcheoConverter.exceptions import ComparisonError

logger = logging.getLogger("acheoconverter.comparator")

MATCH_BY_OPTIONS = ("id", "name", "id_then_name")


# --------------------------------------------------------------------- #
# Result schemas
# --------------------------------------------------------------------- #
class FieldChange(BaseModel):
    """One changed field of a matched element/relationship."""

    field: str
    old: Any
    new: Any


class ElementDiff(BaseModel):
    """A modified element (matched between both models)."""

    base_id: str
    other_id: str
    name: str
    changes: dict[str, FieldChange] = Field(default_factory=dict)


class RelationshipDiff(BaseModel):
    """A modified relationship (matched between both models)."""

    base_id: str
    other_id: str
    changes: dict[str, FieldChange] = Field(default_factory=dict)


class FolderDiff(BaseModel):
    """A modified folder (matched between both models)."""

    base_id: str
    other_id: str
    name: str
    changes: dict[str, FieldChange] = Field(default_factory=dict)
    elements_added: list[str] = Field(default_factory=list)
    elements_removed: list[str] = Field(default_factory=list)


class EntityRef(BaseModel):
    """Reference to an entity that exists on one side only."""

    id: str
    name: str
    type: str = ""


class EntitySection(BaseModel):
    """Added / removed / modified entities for one entity class."""

    added: list[EntityRef] = Field(default_factory=list)
    removed: list[EntityRef] = Field(default_factory=list)
    modified: list[ElementDiff | RelationshipDiff | FolderDiff] = Field(default_factory=list)


class ComparisonResult(BaseModel):
    """Full comparison between two models."""

    base_id: str
    other_id: str
    base_name: str
    other_name: str
    match_by: str
    elements: EntitySection = Field(default_factory=EntitySection)
    relationships: EntitySection = Field(default_factory=EntitySection)
    folders: EntitySection = Field(default_factory=EntitySection)
    totals: dict[str, int] = Field(default_factory=dict)


class Operation(BaseModel):
    """One modification of an integration plan."""

    op: str  # add_folder | update_folder | remove_folder | add_element | update_element | remove_element | add_relationship | update_relationship | remove_relationship
    target_id: str
    payload: dict[str, Any] = Field(default_factory=dict)


class IntegrationPlan(BaseModel):
    """Ordered list of modifications merging the source model into the base."""

    base_id: str
    source_id: str
    include_removals: bool = False
    operations: list[Operation] = Field(default_factory=list)
    summary: dict[str, int] = Field(default_factory=dict)


class ApplyReport(BaseModel):
    """Result of applying an integration plan to a model."""

    base_id: str
    operations_total: int
    applied: int
    skipped: int
    warnings: list[str] = Field(default_factory=list)
    element_count: int = 0
    relationship_count: int = 0
    folder_count: int = 0


# --------------------------------------------------------------------- #
# Service
# --------------------------------------------------------------------- #
class ComparatorService:
    """Compares models and builds/applies integration plans."""

    def __init__(self, default_match_by: str = "id_then_name") -> None:
        if default_match_by not in MATCH_BY_OPTIONS:
            default_match_by = "id_then_name"
        self._default_match_by = default_match_by

    # ------------------------------------------------------------------ #
    # Comparison
    # ------------------------------------------------------------------ #
    def compare(
        self,
        base: Model,
        other: Model,
        *,
        match_by: str | None = None,
    ) -> ComparisonResult:
        """Compare two models and report every difference.

        Args:
            base: the reference model.
            other: the model to compare against ``base``.
            match_by: matching strategy (default from configuration).

        Raises:
            ComparisonError: when the models use different formalisms.
        """
        if base.metadata.formalism != other.metadata.formalism:
            raise ComparisonError(
                f"Cannot compare models with different formalisms "
                f"('{base.metadata.formalism}' vs '{other.metadata.formalism}'). "
                "Convert one of them first.",
            )
        match_by = (match_by or self._default_match_by).lower()
        if match_by not in MATCH_BY_OPTIONS:
            raise ComparisonError(
                f"Invalid match_by '{match_by}'.",
                details=[f"options: {', '.join(MATCH_BY_OPTIONS)}"],
            )

        element_matches = self._match_ids(base.elements, other.elements, match_by)
        rel_matches = self._match_ids(base.relationships, other.relationships, match_by)
        folder_matches = self._match_ids(base.folders, other.folders, match_by)

        elements = self._diff_elements(base, other, element_matches)
        relationships = self._diff_relationships(base, other, rel_matches)
        folders = self._diff_folders(base, other, folder_matches)

        totals = {
            "elements_added": len(elements.added),
            "elements_removed": len(elements.removed),
            "elements_modified": len(elements.modified),
            "relationships_added": len(relationships.added),
            "relationships_removed": len(relationships.removed),
            "relationships_modified": len(relationships.modified),
            "folders_added": len(folders.added),
            "folders_removed": len(folders.removed),
            "folders_modified": len(folders.modified),
        }
        result = ComparisonResult(
            base_id=base.model_id,
            other_id=other.model_id,
            base_name=base.metadata.name,
            other_name=other.metadata.name,
            match_by=match_by,
            elements=elements,
            relationships=relationships,
            folders=folders,
            totals=totals,
        )
        logger.info(
            "compared %s vs %s: added=%d/%d/%d removed=%d/%d/%d modified=%d/%d/%d",
            base.model_id, other.model_id,
            totals["elements_added"], totals["relationships_added"], totals["folders_added"],
            totals["elements_removed"], totals["relationships_removed"], totals["folders_removed"],
            totals["elements_modified"], totals["relationships_modified"], totals["folders_modified"],
        )
        return result

    # ------------------------------------------------------------------ #
    # Integration plan
    # ------------------------------------------------------------------ #
    def integration_plan(
        self,
        base: Model,
        source: Model,
        *,
        include_removals: bool = False,
        match_by: str | None = None,
    ) -> IntegrationPlan:
        """List the modifications required to merge ``source`` into ``base``.

        The plan is *additive by default*: it adds folders/elements/
        relationships from ``source`` that are missing in ``base`` and
        updates the matched ones. Removals are included only when
        ``include_removals`` is True.

        Note: matching always uses ``id_then_name`` semantics so that plan
        ids remain valid when the plan is applied.
        """
        if base.metadata.formalism != source.metadata.formalism:
            raise ComparisonError(
                "Cannot plan an integration between different formalisms. "
                "Convert one of the models first."
            )
        diff = self.compare(base, source, match_by="id_then_name")
        operations: list[Operation] = []

        # --- folders (added first: elements reference them) ------------- #
        for ref in diff.folders.added:
            folder = source.folders[ref.id]
            operations.append(Operation(
                op="add_folder",
                target_id=folder.id,
                payload={
                    "id": folder.id,
                    "name": folder.name,
                    "kind": folder.kind,
                    "parent_id": folder.parent_id
                    if (folder.parent_id is None or folder.parent_id in base.folders
                        or folder.parent_id in {r.id for r in diff.folders.added})
                    else None,
                    "description": folder.description,
                },
            ))
        for mod in diff.folders.modified:
            change_map = {c.field: c for c in mod.changes.values()}
            payload: dict[str, Any] = {}
            if "name" in change_map:
                payload["name"] = change_map["name"].new
            if "kind" in change_map:
                payload["kind"] = change_map["kind"].new
            if "description" in change_map:
                payload["description"] = change_map["description"].new
            payload["elements_added"] = mod.elements_added
            payload["elements_removed"] = mod.elements_removed
            operations.append(Operation(
                op="update_folder", target_id=mod.base_id, payload=payload
            ))
        if include_removals:
            for ref in diff.folders.removed:
                operations.append(Operation(
                    op="remove_folder", target_id=ref.id,
                    payload={"name": ref.name},
                ))

        # --- elements ----------------------------------------------------- #
        for ref in diff.elements.added:
            element = source.elements[ref.id]
            folder_id = element.folder_id
            if folder_id is not None and folder_id not in base.folders \
                    and folder_id not in {r.id for r in diff.folders.added}:
                folder_id = None  # the containing folder is not part of the plan
            operations.append(Operation(
                op="add_element",
                target_id=element.id,
                payload={
                    "id": element.id,
                    "name": element.name,
                    "type": element.type,
                    "stereotypes": list(element.stereotypes),
                    "description": element.description,
                    "visibility": element.visibility,
                    "folder_id": folder_id,
                    "properties": dict(element.properties),
                },
            ))
        for mod in diff.elements.modified:
            operations.append(Operation(
                op="update_element",
                target_id=mod.base_id,
                payload={change.field: _payload_value(change) for change in mod.changes.values()},
            ))
        if include_removals:
            for ref in diff.elements.removed:
                operations.append(Operation(
                    op="remove_element", target_id=ref.id,
                    payload={"name": ref.name, "type": ref.type},
                ))

        # --- relationships ------------------------------------------------- #
        for ref in diff.relationships.added:
            rel = source.relationships[ref.id]
            operations.append(Operation(
                op="add_relationship",
                target_id=rel.id,
                payload={
                    "id": rel.id,
                    "source": rel.source,
                    "target": rel.target,
                    "type": rel.type,
                    "aggregation": rel.aggregation,
                    "qualified_name": rel.qualified_name,
                },
            ))
        for mod in diff.relationships.modified:
            operations.append(Operation(
                op="update_relationship",
                target_id=mod.base_id,
                payload={change.field: _payload_value(change) for change in mod.changes.values()},
            ))
        if include_removals:
            for ref in diff.relationships.removed:
                operations.append(Operation(
                    op="remove_relationship", target_id=ref.id,
                    payload={"name": ref.name},
                ))

        summary: dict[str, int] = {}
        for operation in operations:
            summary[operation.op] = summary.get(operation.op, 0) + 1
        plan = IntegrationPlan(
            base_id=base.model_id,
            source_id=source.model_id,
            include_removals=include_removals,
            operations=operations,
            summary=summary,
        )
        logger.info(
            "integration plan built: base=%s source=%s operations=%d",
            base.model_id, source.model_id, len(operations),
        )
        return plan

    # ------------------------------------------------------------------ #
    # Plan application
    # ------------------------------------------------------------------ #
    def apply_plan(self, base: Model, plan: IntegrationPlan) -> tuple[Model, ApplyReport]:
        """Apply ``plan`` to a copy of ``base`` and return (merged, report).

        The original model is never mutated. Operations whose preconditions
        are not met (missing endpoints, unknown folders) are skipped with a
        warning instead of failing the whole plan.
        """
        merged = base.model_copy(deep=True)
        report = ApplyReport(base_id=base.model_id, operations_total=len(plan.operations))

        for operation in plan.operations:
            try:
                self._apply_operation(merged, operation)
                report.applied += 1
            except _PlanSkip as skip:
                report.skipped += 1
                report.warnings.append(f"[{operation.op} {operation.target_id}] {skip}")
        report.element_count = len(merged.elements)
        report.relationship_count = len(merged.relationships)
        report.folder_count = len(merged.folders)
        return merged, report

    def _apply_operation(self, model: Model, operation: Operation) -> None:
        """Apply one plan operation to ``model`` (raises _PlanSkip on issues)."""
        op, payload = operation.op, operation.payload

        if op == "add_folder":
            folder = ModelFolder.model_validate(payload)
            if folder.id in model.folders:
                raise _PlanSkip("folder id already exists")
            if folder.parent_id is not None and folder.parent_id not in model.folders:
                folder.parent_id = None
            model.folders[folder.id] = folder
        elif op == "update_folder":
            folder = model.folders.get(operation.target_id)
            if folder is None:
                raise _PlanSkip("folder not found")
            for key in ("name", "kind", "description"):
                if key in payload:
                    setattr(folder, key, payload[key])
            for eid in payload.get("elements_added", []):
                if eid in model.elements and eid not in folder.element_ids:
                    folder.element_ids.append(eid)
            folder.element_ids = [eid for eid in folder.element_ids
                                  if eid not in set(payload.get("elements_removed", []))]
        elif op == "remove_folder":
            folder = model.folders.pop(operation.target_id, None)
            if folder is None:
                raise _PlanSkip("folder not found")
            for child in list(model.folders.values()):
                if child.parent_id == operation.target_id:
                    child.parent_id = None
        elif op == "add_element":
            element = ModelElement.model_validate(payload)
            if element.id in model.elements:
                raise _PlanSkip("element id already exists")
            if element.folder_id is not None and element.folder_id not in model.folders:
                element.folder_id = None
            model.elements[element.id] = element
            if element.folder_id is not None:
                model.folders[element.folder_id].element_ids.append(element.id)
        elif op == "update_element":
            element = model.elements.get(operation.target_id)
            if element is None:
                raise _PlanSkip("element not found")
            for key, value in payload.items():
                if key in ("name", "type", "description", "visibility", "stereotypes",
                           "properties", "folder_id"):
                    setattr(element, key, value)
            old_folder = element.folder_id
            if "folder_id" in payload and old_folder:
                old = model.folders.get(old_folder)
                if old and operation.target_id in old.element_ids:
                    old.element_ids.remove(operation.target_id)
            if element.folder_id is not None:
                folder = model.folders.get(element.folder_id)
                if folder and element.id not in folder.element_ids:
                    folder.element_ids.append(element.id)
        elif op == "remove_element":
            element = model.elements.pop(operation.target_id, None)
            if element is None:
                raise _PlanSkip("element not found")
            for folder in model.folders.values():
                if element.id in folder.element_ids:
                    folder.element_ids.remove(element.id)
            for rid in [r for r, rel in model.relationships.items()
                        if rel.source == element.id or rel.target == element.id]:
                del model.relationships[rid]
        elif op == "add_relationship":
            rel = ModelRelationship.model_validate(payload)
            if rel.id in model.relationships:
                raise _PlanSkip("relationship id already exists")
            if rel.source not in model.elements or rel.target not in model.elements:
                raise _PlanSkip("endpoint missing in merged model")
            model.relationships[rel.id] = rel
        elif op == "update_relationship":
            rel = model.relationships.get(operation.target_id)
            if rel is None:
                raise _PlanSkip("relationship not found")
            for key, value in payload.items():
                if key in ("source", "target", "type", "aggregation", "qualified_name"):
                    setattr(rel, key, value)
        elif op == "remove_relationship":
            if model.relationships.pop(operation.target_id, None) is None:
                raise _PlanSkip("relationship not found")
        else:
            raise _PlanSkip(f"unknown operation '{op}'")

    # ------------------------------------------------------------------ #
    # Matching & diffing internals
    # ------------------------------------------------------------------ #
    @staticmethod
    def _match_ids(
        base: dict[str, Any],
        other: dict[str, Any],
        match_by: str,
    ) -> tuple[list[tuple[str, str]], set[str], set[str]]:
        """Match entities by id (and optionally by name).

        Returns ``(matches, base_unmatched, other_unmatched)`` where
        ``matches`` is a list of ``(base_id, other_id)`` pairs.
        """
        matches: list[tuple[str, str]] = []
        if match_by == "id":
            for base_id in base:
                if base_id in other:
                    matches.append((base_id, base_id))
            base_unmatched = {b for b in base if b not in other}
            other_unmatched = {o for o in other if o not in base}
            return matches, base_unmatched, other_unmatched

        # id pass
        for base_id in base:
            if base_id in other:
                matches.append((base_id, base_id))
        base_unmatched = [b for b in base if b not in other]
        other_unmatched = [o for o in other if o not in base]
        if match_by == "id_then_name":
            # name pass over the remainder (case-insensitive exact name)
            by_name: dict[str, list[str]] = {}
            for oid in other_unmatched:
                by_name.setdefault(str(other[oid].name).lower(), []).append(oid)
            still_other: set[str] = set(other_unmatched)
            new_base_unmatched: list[str] = []
            for bid in base_unmatched:
                candidates = by_name.get(str(base[bid].name).lower(), [])
                matched = next((oid for oid in candidates if oid in still_other), None)
                if matched is not None:
                    matches.append((bid, matched))
                    still_other.discard(matched)
                else:
                    new_base_unmatched.append(bid)
            return matches, set(new_base_unmatched), still_other
        # match_by == "name": single name pass over everything
        by_name = {}
        for oid in other:
            by_name.setdefault(str(other[oid].name).lower(), []).append(oid)
        matches = []
        base_unmatched_ids: set[str] = set()
        taken: set[str] = set()
        for bid in base:
            candidates = by_name.get(str(base[bid].name).lower(), [])
            matched = next((oid for oid in candidates if oid not in taken), None)
            if matched is not None:
                matches.append((bid, matched))
                taken.add(matched)
            else:
                base_unmatched_ids.add(bid)
        other_unmatched_ids = {o for o in other if o not in taken}
        return matches, base_unmatched_ids, other_unmatched_ids

    @staticmethod
    def _element_changes(base_el: ModelElement, other_el: ModelElement) -> dict[str, FieldChange]:
        changes: dict[str, FieldChange] = {}
        if base_el.name != other_el.name:
            changes["name"] = FieldChange(field="name", old=base_el.name, new=other_el.name)
        if base_el.type != other_el.type:
            changes["type"] = FieldChange(field="type", old=base_el.type, new=other_el.type)
        base_st, other_st = set(base_el.stereotypes), set(other_el.stereotypes)
        if base_st != other_st:
            changes["stereotypes"] = FieldChange(
                field="stereotypes",
                old={"added": sorted(base_st - other_st), "removed": sorted(other_st - base_st)},
                new=sorted(other_st),
            )
        if base_el.description != other_el.description:
            changes["description"] = FieldChange(
                field="description", old=base_el.description, new=other_el.description
            )
        base_props = {k: v for k, v in base_el.properties.items() if not k.startswith("__")}
        other_props = {k: v for k, v in other_el.properties.items() if not k.startswith("__")}
        if base_props != other_props:
            prop_change: dict[str, Any] = {}
            for key in set(base_props) | set(other_props):
                if key not in base_props:
                    prop_change[key] = {"added": other_props[key]}
                elif key not in other_props:
                    prop_change[key] = {"removed": base_props[key]}
                elif base_props[key] != other_props[key]:
                    prop_change[key] = {"old": base_props[key], "new": other_props[key]}
            changes["properties"] = FieldChange(
                field="properties", old=base_props, new=other_props
            )
            changes["properties"].new = other_props  # keep full new state
            changes["properties"].old = {"changed": prop_change, "full": base_props}
        return changes

    def _diff_elements(
        self,
        base: Model,
        other: Model,
        matches: tuple[list[tuple[str, str]], set[str], set[str]],
    ) -> EntitySection:
        matches_list, base_unmatched, other_unmatched = matches
        section = EntitySection()
        for bid in sorted(base_unmatched):
            el = base.elements[bid]
            section.removed.append(EntityRef(id=bid, name=el.name, type=el.type))
        for oid in sorted(other_unmatched):
            el = other.elements[oid]
            section.added.append(EntityRef(id=oid, name=el.name, type=el.type))
        for bid, oid in matches_list:
            changes = self._element_changes(base.elements[bid], other.elements[oid])
            if changes:
                section.modified.append(ElementDiff(
                    base_id=bid, other_id=oid,
                    name=other.elements[oid].name or base.elements[bid].name,
                    changes=changes,
                ))
        return section

    @staticmethod
    def _rel_changes(base_rel: ModelRelationship, other_rel: ModelRelationship) -> dict[str, FieldChange]:
        changes: dict[str, FieldChange] = {}
        for field in ("source", "target", "type", "aggregation"):
            base_value = getattr(base_rel, field)
            other_value = getattr(other_rel, field)
            if base_value != other_value:
                changes[field] = FieldChange(field=field, old=base_value, new=other_value)
        return changes

    def _diff_relationships(
        self,
        base: Model,
        other: Model,
        matches: tuple[list[tuple[str, str]], set[str], set[str]],
    ) -> EntitySection:
        matches_list, base_unmatched, other_unmatched = matches
        section = EntitySection()

        def rel_label(rel: ModelRelationship) -> str:
            return f"{rel.source} -{rel.type}-> {rel.target}"

        for bid in sorted(base_unmatched):
            section.removed.append(EntityRef(id=bid, name=rel_label(base.relationships[bid]),
                                             type=base.relationships[bid].type))
        for oid in sorted(other_unmatched):
            section.added.append(EntityRef(id=oid, name=rel_label(other.relationships[oid]),
                                           type=other.relationships[oid].type))
        for bid, oid in matches_list:
            changes = self._rel_changes(base.relationships[bid], other.relationships[oid])
            if changes:
                section.modified.append(RelationshipDiff(
                    base_id=bid, other_id=oid, changes=changes
                ))
        return section

    def _diff_folders(
        self,
        base: Model,
        other: Model,
        matches: tuple[list[tuple[str, str]], set[str], set[str]],
    ) -> EntitySection:
        matches_list, base_unmatched, other_unmatched = matches
        section = EntitySection()
        for bid in sorted(base_unmatched):
            section.removed.append(EntityRef(id=bid, name=base.folders[bid].name,
                                             type=base.folders[bid].kind))
        for oid in sorted(other_unmatched):
            section.added.append(EntityRef(id=oid, name=other.folders[oid].name,
                                           type=other.folders[oid].kind))
        for bid, oid in matches_list:
            b, o = base.folders[bid], other.folders[oid]
            changes: dict[str, FieldChange] = {}
            for field in ("name", "kind", "description"):
                if getattr(b, field) != getattr(o, field):
                    changes[field] = FieldChange(field=field,
                                                 old=getattr(b, field),
                                                 new=getattr(o, field))
            added = sorted(set(o.element_ids) - set(b.element_ids))
            removed = sorted(set(b.element_ids) - set(o.element_ids))
            if changes or added or removed:
                section.modified.append(FolderDiff(
                    base_id=bid, other_id=oid, name=o.name or b.name,
                    changes=changes, elements_added=added, elements_removed=removed,
                ))
        return section


class _PlanSkip(Exception):
    """Internal: an operation cannot be applied (skipped with a warning)."""


def _payload_value(change: FieldChange) -> Any:
    """Convert a FieldChange into the value to set during plan application.

    The ``stereotypes`` and ``properties`` changes carry their full new
    value in ``new``; simple fields carry the new scalar value.
    """
    if change.field in ("stereotypes", "properties"):
        return change.new
    return change.new
