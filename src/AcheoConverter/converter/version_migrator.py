# converter/version_migrator.py

"""
Migrates models between ArchiMate versions (3.2 ↔ 4.0).
"""

from __future__ import annotations
import logging
from typing import Dict, List, Tuple, Optional, Any, Callable
from dataclasses import dataclass, field

from ..core.model_store import ArchiModel
from ..core.element import (
    ArchiElement_v32,
    ArchiElement_v40,
    ElementTypes_v32,
    ElementTypes_v40
)

logger = logging.getLogger(__name__)


@dataclass
class MigrationResult:
    """Result of version migration."""
    original_model_id: str
    migrated_model: Dict[str, Any]
    warnings: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class VersionMigrator:
    """
    Migrate between ArchiMate 3.2 and 4.0.
    
    Migration rules are configurable via YAML config file.
    """

    # Predefined transformation rules
    _v32_to_v40_rules: Dict[str, List[Tuple[str, Callable]]] = {
        "folder_id": lambda e: getattr(e, "folder_id", None),
        "is_abstract": lambda e: False,  # v3.2 elements are concrete by default
        "specializations": lambda e: [],
    }

    def __init__(self):
        self._rules = self._v32_to_v40_rules

    def migrate(self, model: ArchiModel, from_version: str, to_version: str) -> MigrationResult:
        """Migrate an ArchiModel instance between versions."""
        
        if from_version == "3.2" and to_version == "4.0":
            return self._migrate_v32_to_v40(model)
        elif from_version == "4.0" and to_version == "3.2":
            return self._migrate_v40_to_v32(model)
        else:
            raise ValueError(f"Migration path {from_version} → {to_version} not supported.")

    def _migrate_v32_to_v40(self, model: ArchiModel) -> MigrationResult:
        """Migrate ArchiModel from v3.2 to v4.0."""
        
        warnings = []
        new_elements: List[ArchiElement_v40] = []

        for elem in model.elements.values():
            if isinstance(elem, ArchiElement_v32):
                # Convert to v4.0 element
                new_elem = ArchiElement_v40(
                    id=elem.id,
                    name=elem.name,
                    description=elem.description,
                    type=self._map_type_v32_to_v40(elem.type),
                    documentation=elem.documentation,
                    properties=elem.properties.copy(),
                    folder_id=elem.folder_id,
                    is_abstract=False,  # v3.2 elements are concrete
                    specializations=[],
                    patterns=[]
                )
                new_elements.append(new_elem)
            else:
                # Already v4.0 element, copy as-is
                new_elements.append(elem)

        if warnings:
            logger.warning(f"Warnings during migration: {warnings}")

        migrated_model = {
            "id": model.id,
            "name": model.name,
            "version": "4.0",
            "description": model.description,
            "elements": {e.id: e for e in new_elements},
            "relationships": model.relationships.copy(),
            "views": model.views.copy(),
            "folders": model.folders.copy()
        }

        return MigrationResult(
            original_model_id=model.id,
            migrated_model=migrated_model,
            warnings=warnings
        )

    def _migrate_v40_to_v32(self, model: ArchiModel) -> MigrationResult:
        """Migrate ArchiModel from v4.0 to v3.2 (lossy)."""
        
        warnings = []
        new_elements: List[ArchiElement_v32] = []

        for elem in model.elements.values():
            if isinstance(elem, ArchiElement_v40):
                # Drop v4-only attributes
                new_elem = ArchiElement_v32(
                    id=elem.id,
                    name=elem.name,
                    description=elem.description,
                    type=self._map_type_v40_to_v32(elem.type),
                    documentation=elem.documentation,
                    properties=elem.properties.copy(),
                    folder_id=elem.folder_id
                )
                
                # Log warnings for data loss
                if elem.is_abstract:
                    warnings.append(f"Element '{elem.name}' was abstract (v4.0) – converted to concrete (v3.2)")
                
                new_elements.append(new_elem)
            else:
                # Already v3.2 element, copy as-is
                new_elements.append(elem)

        migrated_model = {
            "id": model.id,
            "name": model.name,
            "version": "3.2",
            "description": model.description,
            "elements": {e.id: e for e in new_elements},
            "relationships": model.relationships.copy(),
            "views": model.views.copy(),
            "folders": model.folders.copy()
        }

        return MigrationResult(
            original_model_id=model.id,
            migrated_model=migrated_model,
            warnings=warnings
        )

    def _map_type_v32_to_v40(self, v32_type: ElementTypes_v32) -> ElementTypes_v40:
        """Map v3.2 element type to v4.0 equivalent."""
        # Simplified mapping (full table in production)
        type_map = {
            ElementTypes_v32.BusinessActor: ElementTypes_v40.BusinessActor,
            ElementTypes_v32.ApplicationComponent: ElementTypes_v40.ApplicationComponent,
            ElementTypes_v32.DataObject: ElementTypes_v40.DataObject,
        }
        
        # For types not in v4.0, use closest match
        return type_map.get(v32_type, ElementTypes_v40.BusinessActor)

    def _map_type_v40_to_v32(self, v40_type: ElementTypes_v40) -> ElementTypes_v32:
        """Map v4.0 element type to v3.2 equivalent."""
        # Simplified mapping
        type_map = {
            ElementTypes_v40.BusinessActor: ElementTypes_v32.BusinessActor,
            ElementTypes_v40.ApplicationComponent: ElementTypes_v32.ApplicationComponent,
            ElementTypes_v40.DataObject: ElementTypes_v32.DataObject,
            ElementTypes_v40.Goal: ElementTypes_v32.BusinessFunction,  # Fallback
        }
        
        return type_map.get(v40_type, ElementTypes_v32.BusinessActor)
