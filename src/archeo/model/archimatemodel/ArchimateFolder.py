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
    # The constructor of ArchimateFolder calls the constructor of ElementBase to initialize the name, type, parentFolder, referenceId, sourcesId, description and standardName attributes with validation.
    def __init__(self,
                pName: str,
                pType: str,
                pParentFolder: Optional[ArchimateFolder] = None,
                pReferenceId: Optional[IdentityPart] = None,
                pSourcesId: Optional[List[IdentityPart]] = None,
                pDescription: Optional[str] = None,
                pStandardName: Optional[str] = None):

        super().__init__(pName,
                         pType,
                         pReferenceId,
                         pSourcesId,
                         pDescription)