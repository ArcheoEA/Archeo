from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from pydantic import BaseModel

from app.models.base import BaseElement, Relationship, ArchiMateVersion

class ArchiMateModel(BaseModel):
    model_id: str
    name: str
    version: ArchiMateVersion
    elements: Dict[str, BaseElement] = {}
    relationships: List[Relationship] = []

class BaseStore(ABC):
    """Abstract Interface for all Storage Systems"""
    @abstractmethod
    def add_model(self, model: ArchiMateModel): pass
    
    @abstractmethod
    def get_model(self, model_id: str) -> Optional[ArchiMateModel]: pass
    
    @abstractmethod
    def list_models(self) -> List[str]: pass
    
    @abstractmethod
    def search_elements(self, model_id: str, query: str) -> List[BaseElement]: pass

class InMemStore(BaseStore):
    """Original In-Memory Implementation"""
    def __init__(self):
        self._models: Dict[str, ArchiMateModel] = {}

    def add_model(self, model: ArchiMateModel):
        self._models[model.model_id] = model

    def get_model(self, model_id: str) -> Optional[ArchiMateModel]:
        return self._models.get(model_id)

    def list_models(self) -> List[str]:
        return list(self._models.keys())

    def search_elements(self, model_id: str, query: str) -> List[BaseElement]:
        model = self.get_model(model_id)
        if not model: return []
        return [e for e in model.elements.values() if query.lower() in e.name.lower()]
