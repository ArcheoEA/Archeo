"""Summary and reporting features."""

from collections import Counter

from .models import ArchiMateModel
from .comparator import DiffReport
from .logger_setup import get_logger

logger = get_logger(__name__)

def generate_model_summary(model: ArchiMateModel) -> dict:
    """Generate a summary report of the model."""
    logger.info("Generating model summary")
    type_counts = Counter(elem.type for elem in model.elements.values())
    return {
        "model_id": model.id,
        "model_name": model.name,
        "version": model.version,
        "total_elements": len(model.elements),
        "total_relationships": len(model.relationships),
        "total_views": len(model.views),
        "element_type_distribution": dict(type_counts),
        "metadata": model.metadata
    }

def generate_diff_summary(report: "DiffReport") -> dict:
    """Generate a summary of model differences."""
    return {
        "added_elements": len(report.added_elements),
        "removed_elements": len(report.removed_elements),
        "modified_elements": len(report.modified_elements),
        "added_relationships": len(report.added_relationships),
        "removed_relationships": len(report.removed_relationships),
        "modified_relationships": len(report.modified_relationships)
    }
