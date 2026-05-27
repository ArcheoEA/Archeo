from archeo.model.basemodel.ModelBase import ModelBase

from dataclasses import dataclass
from typing import Any, List, Optional, Self

# The ModelArchimate class inherits from ModelBase and represents a base class for Archimate models.
# It includes a constructor that initializes the name, formalism, version, customization, and description attributes
# with validation to ensure that name, formalism, and version are not empty or None.
# The constructor calls the constructor of ModelBase to perform the initialization and validation.
@dataclass
class ModelArchimate(ModelBase):
    # The constructor of ElementArchimate calls the constructor of ModelBase to initialize the name, formalism, version, customization, and description attributes with validation.
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
