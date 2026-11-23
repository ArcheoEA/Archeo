"""Summarization and reporting service.

Produces compact, API-friendly summaries of:

* a single model: element/relationship/folder counts, type histograms,
  folder statistics, orphan elements and dangling references;
* a comparison result: per-category counts and the most significant
  differences;

and renders both as **Markdown** for human consumption (the UI and the
API expose both the structured JSON and the rendered text).
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

from ArcheoConverter.core.models import Model
from ArcheoConverter.formalisms.archimate.types import element_display, relationship_display
from ArcheoConverter.services.comparator import ComparisonResult

logger = logging.getLogger("archeoconverter.summarizer")


class FolderStat(BaseModel):
    """Statistics of one folder."""

    id: str
    name: str
    kind: str
    parent_id: str | None
    element_count: int = 0


class DanglingRef(BaseModel):
    """A relationship whose endpoints do not all exist in the model."""

    relationship_id: str
    type: str
    missing: list[str] = Field(default_factory=list)


class ModelSummary(BaseModel):
    """Structured summary of one model."""

    model_id: str
    name: str
    formalism: str
    version: str
    source_file: str | None
    element_count: int
    relationship_count: int
    folder_count: int
    elements_by_type: dict[str, int] = Field(default_factory=dict)
    relationships_by_type: dict[str, int] = Field(default_factory=dict)
    folders: list[FolderStat] = Field(default_factory=list)
    orphan_elements: int = 0
    dangling_relationships: list[DanglingRef] = Field(default_factory=list)
    distinct_stereotypes: int = 0
    distinct_tags: int = 0


class ComparisonSummary(BaseModel):
    """Structured summary of a comparison result."""

    base_id: str
    other_id: str
    base_name: str
    other_name: str
    totals: dict[str, int] = Field(default_factory=dict)
    notable: list[str] = Field(default_factory=list)


class SummarizerService:
    """Builds model and comparison summaries (JSON + Markdown)."""

    def summarize(self, model: Model) -> ModelSummary:
        """Build the structured summary of a model."""
        elements_by_type: dict[str, int] = {}
        relationships_by_type: dict[str, int] = {}
        stereotypes: set[str] = set()
        tags: set[str] = set()
        involved: set[str] = set()

        for element in model.elements.values():
            elements_by_type[element.type] = elements_by_type.get(element.type, 0) + 1
            stereotypes.update(element.stereotypes)
            element_tags = element.properties.get("__tags") or []
            tags.update(element_tags)
        for rel in model.relationships.values():
            relationships_by_type[rel.type] = relationships_by_type.get(rel.type, 0) + 1
            involved.add(rel.source)
            involved.add(rel.target)

        folders = [
            FolderStat(
                id=folder.id,
                name=folder.name,
                kind=folder.kind,
                parent_id=folder.parent_id,
                element_count=len(folder.element_ids),
            )
            for folder in sorted(model.folders.values(), key=lambda f: f.name.lower())
        ]

        dangling = []
        for rel in model.relationships.values():
            missing = [endpoint for endpoint in (rel.source, rel.target)
                       if endpoint not in model.elements]
            if missing:
                dangling.append(DanglingRef(
                    relationship_id=rel.id, type=rel.type, missing=missing
                ))

        summary = ModelSummary(
            model_id=model.model_id,
            name=model.metadata.name,
            formalism=model.metadata.formalism,
            version=model.metadata.version,
            source_file=model.metadata.source_file,
            element_count=len(model.elements),
            relationship_count=len(model.relationships),
            folder_count=len(model.folders),
            elements_by_type=dict(sorted(elements_by_type.items(),
                                         key=lambda kv: (-kv[1], kv[0]))),
            relationships_by_type=dict(sorted(relationships_by_type.items(),
                                              key=lambda kv: (-kv[1], kv[0]))),
            folders=folders,
            orphan_elements=sum(1 for eid in model.elements if eid not in involved),
            dangling_relationships=dangling,
            distinct_stereotypes=len(stereotypes),
            distinct_tags=len(tags),
        )
        logger.debug("summarized model %s: %d elements, %d relationships",
                     model.model_id, summary.element_count, summary.relationship_count)
        return summary

    # ------------------------------------------------------------------ #
    # Comparison summary
    # ------------------------------------------------------------------ #
    def summarize_comparison(self, result: ComparisonResult) -> ComparisonSummary:
        """Build the structured summary of a comparison result."""
        notable: list[str] = []
        if result.elements.modified:
            first = result.elements.modified[0]
            fields = ", ".join(first.changes.keys())
            notable.append(
                f"{len(result.elements.modified)} element(s) modified "
                f"(first: '{first.name}' - {fields})"
            )
        if result.elements.added:
            notable.append(f"{len(result.elements.added)} element(s) only in '{result.other_name}'")
        if result.elements.removed:
            notable.append(f"{len(result.elements.removed)} element(s) only in '{result.base_name}'")
        if result.relationships.modified:
            notable.append(f"{len(result.relationships.modified)} relationship(s) modified")
        if result.relationships.added:
            notable.append(f"{len(result.relationships.added)} relationship(s) only in '{result.other_name}'")
        if result.relationships.removed:
            notable.append(f"{len(result.relationships.removed)} relationship(s) only in '{result.base_name}'")
        if result.folders.modified:
            notable.append(f"{len(result.folders.modified)} folder(s) modified")
        return ComparisonSummary(
            base_id=result.base_id,
            other_id=result.other_id,
            base_name=result.base_name,
            other_name=result.other_name,
            totals=dict(result.totals),
            notable=notable,
        )

    # ------------------------------------------------------------------ #
    # Markdown rendering
    # ------------------------------------------------------------------ #
    @staticmethod
    def render_markdown(summary: ModelSummary, version: str | None = None) -> str:
        """Render a :class:`ModelSummary` as a Markdown report."""
        version = version or summary.version
        lines: list[str] = [
            f"# Model summary - {summary.name}",
            "",
            f"| Property | Value |",
            f"| --- | --- |",
            f"| Model id | `{summary.model_id}` |",
            f"| Formalism | {summary.formalism} {summary.version} |",
            f"| Source file | {summary.source_file or '-'} |",
            f"| Elements | {summary.element_count} |",
            f"| Relationships | {summary.relationship_count} |",
            f"| Folders / views | {summary.folder_count} |",
            f"| Orphan elements | {summary.orphan_elements} |",
            f"| Dangling relationships | {len(summary.dangling_relationships)} |",
            "",
            "## Elements by type",
            "",
            "| Type | Count |",
            "| --- | --- |",
        ]
        for type_name, count in summary.elements_by_type.items():
            lines.append(f"| {element_display(type_name, version)} (`{type_name}`) | {count} |")
        lines += [
            "",
            "## Relationships by type",
            "",
            "| Type | Count |",
            "| --- | --- |",
        ]
        for type_name, count in summary.relationships_by_type.items():
            lines.append(f"| {relationship_display(type_name)} (`{type_name}`) | {count} |")
        lines += [
            "",
            "## Folders",
            "",
            "| Folder | Kind | Elements |",
            "| --- | --- | --- |",
        ]
        for folder in summary.folders:
            indent = "" if folder.parent_id is None else "&nbsp;&nbsp;"
            lines.append(f"| {indent}{folder.name} | {folder.kind} | {folder.element_count} |")
        if summary.dangling_relationships:
            lines += ["", "## Dangling relationships", ""]
            for dangling in summary.dangling_relationships:
                lines.append(f"- `{dangling.relationship_id}` ({dangling.type}): "
                             f"missing {', '.join(dangling.missing)}")
        return "\n".join(lines) + "\n"

    @staticmethod
    def render_comparison_markdown(result: ComparisonResult) -> str:
        """Render a :class:`ComparisonResult` as a Markdown report."""
        lines: list[str] = [
            f"# Comparison - {result.base_name} vs {result.other_name}",
            "",
            f"- base model: `{result.base_id}` ({result.base_name})",
            f"- other model: `{result.other_id}` ({result.other_name})",
            f"- matching: {result.match_by}",
            "",
            "| Category | Added (in other) | Removed (in base) | Modified |",
            "| --- | --- | --- | --- |",
            f"| Elements | {result.totals['elements_added']} "
            f"| {result.totals['elements_removed']} "
            f"| {result.totals['elements_modified']} |",
            f"| Relationships | {result.totals['relationships_added']} "
            f"| {result.totals['relationships_removed']} "
            f"| {result.totals['relationships_modified']} |",
            f"| Folders | {result.totals['folders_added']} "
            f"| {result.totals['folders_removed']} "
            f"| {result.totals['folders_modified']} |",
            "",
        ]
        if result.elements.added:
            lines += ["## Elements only in the other model", ""]
            for ref in result.elements.added[:50]:
                lines.append(f"- {ref.name} (`{ref.id}`, {ref.type})")
            if len(result.elements.added) > 50:
                lines.append(f"- ... and {len(result.elements.added) - 50} more")
            lines.append("")
        if result.elements.removed:
            lines += ["## Elements only in the base model", ""]
            for ref in result.elements.removed[:50]:
                lines.append(f"- {ref.name} (`{ref.id}`, {ref.type})")
            if len(result.elements.removed) > 50:
                lines.append(f"- ... and {len(result.elements.removed) - 50} more")
            lines.append("")
        if result.elements.modified:
            lines += ["## Modified elements", ""]
            for mod in result.elements.modified[:50]:
                fields = ", ".join(mod.changes.keys())
                lines.append(f"- {mod.name} (`{mod.base_id}`): {fields}")
            if len(result.elements.modified) > 50:
                lines.append(f"- ... and {len(result.elements.modified) - 50} more")
            lines.append("")
        return "\n".join(lines) + "\n"
