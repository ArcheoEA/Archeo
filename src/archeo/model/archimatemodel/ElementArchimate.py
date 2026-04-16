from archeo.model.basemodel.IdentityPart import IdentityPart
from archeo.model.basemodel.ElementBase import ElementBase

from dataclasses import dataclass
from typing import Any, List, Optional, Self

# The ArchimateBase class inherits from ElementBase and represents a base class for Archimate models.
# It includes a constructor that initializes the name, type, referenceId, sourcesId, and description attributes
# with validation to ensure that name, type, and referenceId are not empty or None.
# The constructor calls the constructor of ElementBase to perform the initialization and validation.
@dataclass
class ArchimateBase(ElementBase):
    # The constructor of ArchimateBase calls the constructor of ElementBase to initialize the name, type, referenceId, sourcesId, and description attributes with validation.
    def __init__(self,
                pName: str,
                pType: str,
                pReferenceId: Optional[IdentityPart] = None,
                pSourcesId: Optional[List[IdentityPart]] = None,
                pDescription: Optional[str] = None):

        super().__init__(pName=pName,
                         pType=pType,
                         pReferenceId=pReferenceId,
                         pSourcesId=pSourcesId,
                         pDescription=pDescription)