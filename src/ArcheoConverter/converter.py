"""Version migration logic (3.2 <-> 4.0)."""

from copy import deepcopy

from .models import ArchiMateModel
from .logger_setup import get_logger

logger = get_logger(__name__)

# ArchiMate 3.2 -> 4.0 type mapping (simplified for core concepts)
TYPE_MAPPING = {
    "BusinessObject": "DataObject",
    "ApplicationObject": "DataObject",
    "TechnologyObject": "Artifact",
    "BusinessProcess": "Process",
    "ApplicationProcess": "Process",
    "TechnologyProcess": "Process",
    "Access": "Access",
    "Assignment": "Assignment",
    "Association": "Association",
    "Composition": "Composition",
    "Derivation": "Derivation",
    "Flow": "Flow",
    "Influence": "Influence",
    "Serving": "Serving",
    "Specialization": "Specialization",
    "Triggering": "Triggering",
    "Using": "Using"
}

def migrate_model(model: ArchiMateModel, target_version: str) -> ArchiMateModel:
    """Migrate model to target ArchiMate version."""
    logger.info(f"Migrating model {model.id} from {model.version} to {target_version}")
    if model.version == target_version:
        return model

    new_model = deepcopy(model)
    new_model.version = target_version

    for elem in new_model.elements.values():
        elem.type = TYPE_MAPPING.get(elem.type, elem.type)

    for rel in new_model.relationships.values():
        rel.type = TYPE_MAPPING.get(rel.type, rel.type)

    logger.info("Migration completed")
    return new_model
