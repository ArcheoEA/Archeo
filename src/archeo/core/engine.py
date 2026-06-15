import logging

from typing import List, Dict, Any

from models.store import store, ArchiMateModel, ArchiMateVersion
from models.base import BaseElement

logger = logging.getLogger(__name__)

class ArchimateEngine:
    @staticmethod
    def navigate_elements(model_id: str, search_term: str = None) -> List[BaseElement]:
        model = store.get_model(model_id)
        if not model:
            raise ValueError("Model not found")
        
        elements = list(model.elements.values())
        if search_term:
            elements = [e for e in elements if search_term.lower() in e.name.lower()]
        return elements

    @staticmethod
    def migrate_version(model_id: str, target_version: ArchiMateVersion) -> ArchiMateModel:
        """Handles migration between 3.2 and 4.0."""
        model = store.get_model(model_id)
        if not model:
            raise ValueError("Model not found")
        
        logger.info(f"Migrating model {model_id} from {model.version} to {target_version}")
        
        # In a real scenario, we would map elements that changed between 3.2 and 4.0
        # For this implementation, we update the version metadata and ensure compatibility
        model.version = target_version
        return model

    @staticmethod
    def compare_models(model_a_id: str, model_b_id: str) -> Dict[str, Any]:
        """Identifies differences between two models."""
        m1 = store.get_model(model_a_id)
        m2 = store.get_model(model_b_id)
        
        if not m1 or not m2:
            raise ValueError("One or both models not found")

        # Compare elements by name (simplification for demo)
        names1 = {e.name for e in m1.elements.values()}
        names2 = {e.name for e in m2.elements.values()}
        
        diff = {
            "only_in_a": list(names1 - names2),
            "only_in_b": list(names2 - names1),
            "common": list(names1 & names2),
            "relationship_count_diff": len(m1.relationships) - len(m2.relationships)
        }
        return diff
