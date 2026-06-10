from archeo.model.basemodel.IdentityPart import IdentityPart
from archeo.model.basemodel.ElementBase import ElementBase

from dataclasses import dataclass
from typing import Any, List, Optional, Self

# The ArchimateFolder class inherits from ElementBase and represents a folder, or sub-folder, used to organize elements into a Archimate model.
# It includes a constructor that initializes the name, type, parentFolder, referenceId, sourcesId, description and standardName attributes
# with validation to ensure that name, type, and referenceId are not empty or None.
# The constructor calls the constructor of ElementBase to perform the initialization and validation.
@dataclass
class ArchimateFolder(ElementBase):
    parentFolder: ArchimateFolder | None
    standardName: str | None

    # The __slots__ declaration is used to optimize memory usage by preventing the creation of a __dict__ for each instance of ElementBase.
    __slots__ = ['name', 'type', 'parentFolder', 'referenceId', 'sourcesId', 'description', 'standardName']

    # The constructor of ArchimateFolder calls the constructor of ElementBase to initialize the name, type, parentFolder, referenceId, sourcesId, description and standardName attributes with validation.
    def __init__(self,
                pName: str,
                pType: str,
                pParentFolder: Optional[ArchimateFolder] = None,
                pReferenceId: Optional[IdentityPart] = None,
                pSourcesId: Optional[List[IdentityPart]] = None,
                pDescription: Optional[str] = None,
                pStandardName: Optional[str] = None):

        try:
            super().__init__(pName,
                            pType,
                            pReferenceId,
                            pSourcesId,
                            pDescription)

            # Initialize parentFolder
            if (pParentFolder is not None) or (not isinstance(pParentFolder, ArchimateFolder)):
                raise ValueError("Empty or wrong parent folder")
            else:
                self.parentFolder = pParentFolder

            # Initialize standardName, and force string "" as value if it's None
            self.standardName = pStandardName if pStandardName is not None else ""

        except ValueError as e:
            print(f"Initialization of ArchimateRelation failed: {e}")

    def __hash__(self) -> int:
        try:
            # Validate that name, type are not empty or None before calculating the hash
            # Attributes parentFolder and standardName are sued only if they're empty or None
            if (self.name is None) or (self.name == "") \
                    or (self.type is None) or (self.type == ""):
                print(f"Hash calculation of ArchimateFolder failed, with name={self.name}, type={self.type}")

                raise ValueError("Invalid name, or type for hashing")
            
            # The hash is based on the name, type, and parentFolder hash (if exist) attributes of the ArchimateFolder
            if (self.parentFolder is not None) and (isinstance(self.parentFolder, ArchimateFolder)):
                return hash((self.name, self.type, self.parentFolder.__hash__()))
            else:
                return hash((self.name, self.type))
            
        except ValueError as e:
            print(f"Hash calculation of ArchimateFolder failed: {e}")

            # Return a default hash value in case of invalid attributes
            return 0
