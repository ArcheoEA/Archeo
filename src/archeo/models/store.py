from pydantic import BaseModel
from typing import Dict, List, Any
from .base import BaseElement, Relationship, ArchiMateVersion

class ArchiMateModel(BaseModel):
    model_id: str
    name: str
    version: ArchiMateVersion
    elements: Dict[str, BaseElement] = {}
    relationships: List[Relationship] = []

class InMemStore:
    """Singleton store for managing multiple models in memory."""
    def __init__(self):
        self._models: Dict[str, ArchiMateModel] = {}

    def add_model(self, model: ArchiMateModel):
        self._models[model.model_id] = model

    def get_model(self, model_id: str) -> ArchiMateModel:
        return self._models.get(model_id)

    def list_models(self) -> List[str]:
        return list(self._models.keys())

# Global instance
store = InMemStore()
