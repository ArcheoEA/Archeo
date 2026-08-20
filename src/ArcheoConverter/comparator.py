"""Model comparison and integration management."""

from dataclasses import dataclass, field
from typing import Optional

from .models import ArchiMateModel
from .logger_setup import get_logger

logger = get_logger(__name__)

@dataclass
class DiffReport:
    added_elements: list[str] = field(default_factory=list)
    removed_elements: list[str] = field(default_factory=list)
    modified_elements: list[str] = field(default_factory=list)
    added_relationships: list[str] = field(default_factory=list)
    removed_relationships: list[str] = field(default_factory=list)
    modified_relationships: list[str] = field(default_factory=list)

def compare_models(model_a: ArchiMateModel, model_b: ArchiMateModel) -> DiffReport:
    """Compare two ArchiMate models and generate a diff report."""
    logger.info("Starting model comparison")
    report = DiffReport()

    elems_a = set(model_a.elements.keys())
    elems_b = set(model_b.elements.keys())
    report.added_elements = list(elems_b - elems_a)
    report.removed_elements = list(elems_a - elems_b)
    common = elems_a & elems_b
    for eid in common:
        if model_a.elements[eid] != model_b.elements[eid]:
            report.modified_elements.append(eid)

    rels_a = set(model_a.relationships.keys())
    rels_b = set(model_b.relationships.keys())
    report.added_relationships = list(rels_b - rels_a)
    report.removed_relationships = list(rels_a - rels_b)
    common_rels = rels_a & rels_b
    for rid in common_rels:
        if model_a.relationships[rid] != model_b.relationships[rid]:
            report.modified_relationships.append(rid)

    logger.info("Comparison completed")
    return report

def integrate_models(source: ArchiMateModel, target: ArchiMateModel, strategy: str = "merge") -> ArchiMateModel:
    """Integrate source model into target model."""
    logger.info(f"Integrating models using strategy: {strategy}")
    if strategy == "merge":
        for k, v in source.elements.items():
            if k not in target.elements:
                target.elements[k] = v
        for k, v in source.relationships.items():
            if k not in target.relationships:
                target.relationships[k] = v
        for k, v in source.views.items():
            if k not in target.views:
                target.views[k] = v
    elif strategy == "override":
        target.elements.update(source.elements)
        target.relationships.update(source.relationships)
        target.views.update(source.views)
    else:
        raise ValueError(f"Unknown integration strategy: {strategy}")
    logger.info("Integration completed")
    return target
