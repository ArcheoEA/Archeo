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

    # The __slots__ declaration is used to optimize memory usage by preventing the creation of a __dict__ for each instance of ElementBase.
    __slots__ = ['name', 'type', 'origElement', 'destElement', 'referenceId', 'sourcesId', 'description']

    # The constructor of ArchimateRelation calls the constructor of ElementBase to initialize the name, type, origElement, destElement, referenceId, sourcesId, and description attributes with validation.
    def __init__(self,
                pName: str,
                pType: str,
                pOrigElement: IdentityPart,
                pDestElement: IdentityPart,
                pReferenceId: Optional[IdentityPart] = None,
                pSourcesId: Optional[List[IdentityPart]] = None,
                pDescription: Optional[str] = None):

        try:
            super().__init__(pName,
                            pType,
                            pReferenceId,
                            pSourcesId,
                            pDescription)

            # Initialize origElement
            if (pOrigElement is None) or (pOrigElement == ""):
                raise ValueError("Origine element cannot be empty")
            else:
                self.origElement = pOrigElement

            # Initialize destElement
            if (pDestElement is None) or (pDestElement == ""):
                raise ValueError("Destination element cannot be empty")
            else:
                self.destElement = pDestElement

        except ValueError as e:
            print(f"Initialization of ArchimateRelation failed: {e}")

    def __hash__(self) -> int:
        try:
            # Validate that name, type, origElement, and destElement are not empty or None before calculating the hash
            if (self.name is None) or (self.name == "") \
                    or (self.type is None) or (self.type == "") \
                    or (self.origElement is None) or (not isinstance(self.origElement, IdentityPart)) \
                    or (self.destElement is None) or (not isinstance(self.destElement, IdentityPart)):
                print(f"Hash calculation of ArchimateRelation failed, with name={self.name}, type={self.type}, origElement={self.origElement}, destElement={self.destElement}")

                raise ValueError("Invalid name, type, origElement, or destElement for hashing")
            
            # The hash is based on the name, type, origElement, and destElement attributes of the ArchimateRelation
            return hash((self.name, self.type, self.origElement.__hash__(), self.destElement.__hash__()))
            
        except ValueError as e:
            print(f"Hash calculation of ArchimateRelation failed: {e}")

            # Return a default hash value in case of invalid attributes
            return 0
