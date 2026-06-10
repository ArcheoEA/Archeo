from archeo.model.basemodel.IdentityPart import IdentityPart
from archeo.model.basemodel.ElementBase import ElementBase

from dataclasses import dataclass
from typing import Any, List, Optional, Self

# The ArchimateRelation class inherits from ElementBase and represents a relation used to associate Archimate model elements.
# It includes a constructor that initializes the name, type, origElement, destElement, referenceId, sourcesId, and description attributes
# with validation to ensure that name, type, origElement, destElement, and referenceId are not empty or None.
# The constructor calls the constructor of ElementBase to perform the initialization and validation.
@dataclass
class ArchimateRelation(ElementBase):
    origElement: IdentityPart
    destElement: IdentityPart

    # The constructor of ArchimateRelation calls the constructor of ElementBase to initialize the name, type, origElement, destElement, referenceId, sourcesId, and description attributes with validation.
    def __init__(self,
                pName: str,
                pType: str,
                pOrigElement: IdentityPart,
                pDestElement: IdentityPart,
                pReferenceId: Optional[IdentityPart] = None,
                pSourcesId: Optional[List[IdentityPart]] = None,
                pDescription: Optional[str] = None):

        super().__init__(pName,
                         pType,
                         pReferenceId,
                         pSourcesId,
                         pDescription)

    def __hash__(self) -> int:
        super().__hash__()

