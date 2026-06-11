from __future__ import annotations

from archeo.model.basemodel.ModelBase import ModelBase
from archeo.model.archimatemodel.ArchimateElement import ArchimateElement
from archeo.model.archimatemodel.ArchimateRelation import ArchimateRelation
from archeo.model.archimatemodel.ArchimateFolder import ArchimateFolder

from dataclasses import dataclass, field
from typing import Any, List, Optional, Self

# The ArchimateModel class inherits from ModelBase and represents a base class for Archimate models.
# It includes a constructor that initializes the name, formalism, version, customization, and description attributes
# with validation to ensure that name, formalism, and version are not empty or None.
# The constructor calls the constructor of ModelBase to perform the initialization and validation.
@dataclass
class ArchimateModel(ModelBase):
    name: str
    formalism: str
    version: str | None
    customization: str | None
    description: Optional[str] | None
    
    # Dictionary-like structures for storing Archimate model elements and relationships
    elements: dict[str, ArchimateElement] = field(default_factory=dict)
    relations: dict[str, ArchimateRelation] = field(default_factory=dict)
    
    # Folder trees for model element repository (organization tree) and view repository (view tree)
    organization_tree: ArchimateFolder | None = None
    view_tree: ArchimateFolder | None = None
    
    # The constructor of ArchimateElement calls the constructor of ModelBase to initialize the name, formalism, version, customization, and description attributes with validation.
    def __init__(self,
                pName: str,
                pFormalism: str,
                pVersion: Optional[str] = None,
                pCustomization: Optional[str] = None,
                pDescription: Optional[str] = None):

        super().__init__(pName,
                         pFormalism,
                         pVersion,
                         pCustomization,
                         pDescription)

        # Initialize storage structures
        self.elements: dict[str, ArchimateElement] = {}
        self.relations: dict[str, ArchimateRelation] = {}
        self.organization_tree: ArchimateFolder | None = None
        self.view_tree: ArchimateFolder | None = None

    def __hash__(self) -> int:
        try:
            # Validate that name, formalism, customization are not empty or None before calculating the hash
            if (self.name is None) or (self.name == "") \
                    or (self.formalism is None) or (self.formalism == "") \
                    or (self.customization is None) or (self.customization == ""):
                print(f"Hash calculation of ArchimateModel failed, with name={self.name}, formalism={self.formalism}, customization={self.customization}")

                raise ValueError("Invalid name, type, formalism, or customization for hashing")
            
            # The hash is based on the name, formalism, and customization attributes of the ArchimateModel
            return hash((self.name, self.formalism, self.customization))
            
        except ValueError as e:
            print(f"Hash calculation of ArchimateModel failed: {e}")

            # Return a default hash value in case of invalid attributes
            return 0