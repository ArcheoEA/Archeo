from archeo.model.basemodel.IdentityPart import IdentityPart

from dataclasses import dataclass
from typing import Any, List, Optional, Self
from uuid import uuid4
from datetime import datetime

# The ElementBase class represents an element with attributes such as name, type, referenceId, sourcesId, and description.
# It includes validation in the constructor and post-initialization method to ensure that the name, type, and referenceId are not empty or None.
# The hash of an ElementBase is based on its referenceId.
@dataclass ()
class ElementBase:
    name: str
    type: str
    referenceId: IdentityPart
    sourcesId: List[IdentityPart] | None
    description: Optional[str] | None

    # The __slots__ declaration is used to optimize memory usage by preventing the creation of a __dict__ for each instance of ElementBase.
    __slots__ = ['name', 'type', 'referenceId', 'sourcesId', 'description']

    # The constructor of ElementBase initializes the name, type, referenceId, sourcesId, and description attributes with validation to ensure that name, type, and referenceId are not empty or None.
    def __init__(self,
                pName: str,
                pType: str,
                pReferenceId: Optional[IdentityPart] = None,
                pSourcesId: Optional[List[IdentityPart]] = None,
                pDescription: Optional[str] = None):

        try:
            # Initialize name
            if (pName is None) or (pName == ""):
                raise ValueError("Name cannot be empty")
            else:
                self.name = pName

            # Initialize _type
            if (pType is None) or (pType == ""):
                raise ValueError("Type cannot be empty")
            else:
                self.type = pType

            # Initialize referenceId
            if pReferenceId is None:
                self.referenceId = IdentityPart(pName=self.name, pType=self.type)
            else:
                if not isinstance(pReferenceId, IdentityPart):
                    raise ValueError("ReferenceId must be an instance of IdentityPart")
                else:
                    if (pReferenceId.name == ""):
                        raise ValueError("ReferenceId with empty name isn't allowed")
                    elif (pReferenceId.name != self.name):
                        raise ValueError("ReferenceId name must match the model name")

                    if (pReferenceId.type == ""):
                        raise ValueError("ReferenceId with empty type isn't allowed")
                    elif (pReferenceId.type != self.type):
                        raise ValueError("ReferenceId type must match the model type")

                    self.referenceId = pReferenceId

            # Initialize sourcesId
            if pSourcesId is not None:
                self.sourcesId = pSourcesId

                for source in self.sourcesId:
                    if not isinstance(source, IdentityPart):
                        raise ValueError("All sourcesId must be instances of IdentityPart")
                    else:
                        if (source.name == ""):
                            raise ValueError("sourcesId with empty name isn't allowed")

                        if (source.type == ""):
                            raise ValueError("sourcesId with empty type isn't allowed")

            # Initialize description
            self.description = pDescription if pDescription is not None else None

            # Call the post-initialization method to validate the attributes
            self.__post_init__()

        except ValueError as e:
            print(f"Initialization of ElementBase failed: {e}")

    def __post_init__(self):
        try:
            # Validate that name, type, and referenceId are not empty or None
            if (self.name is None) or (self.name == "") or (self.type is None) or (self.type == "") or (self.referenceId is None) or (not isinstance(self.referenceId, IdentityPart)):
                print(f"Post-initialization of ElementBase failed, with name={self.name}, type={self.type}, referenceId={self.referenceId}")

                raise ValueError("Invalid name, type, or referenceId")

        except ValueError as e:
            print(f"Post-initialization of ElementBase failed: {e}")

    def __hash__(self) -> int:
        try:
            # Validate that name, type, and referenceId are not empty or None before calculating the hash
            if (self.name is None) or (self.name == "") or (self.type is None) or (self.type == "") or (self.referenceId is None) or (not isinstance(self.referenceId, IdentityPart)):
                print(f"Hash calculation of ElementBase failed, with name={self.name}, type={self.type}, referenceId={self.referenceId}")

                raise ValueError("Invalid name, type, or referenceId for hashing")
            
            # The hash is based on the referenceId of the ElementBase
            # None of the other attributes (name, type, sourcesId, description) are included in the hash calculation
            return self.referenceId.__hash__()
            
        except ValueError as e:
            print(f"Hash calculation of ElementBase failed: {e}")

            # Return a default hash value in case of invalid attributes
            return 0

    def __eq__(self, other: Any) -> bool:
        try:
            # Validate that the other object is an instance of ElementBase before comparing
            if not isinstance(other, ElementBase):
                print(f"Equality comparison of ElementBase failed: other object is not an instance of ElementBase")

                raise ValueError("Equality comparison failed: other object is not an instance of ElementBase")

            # Validate that name, type, and referenceId are not empty or None for both instances before comparing
            if (self.name is None) or (self.name == "") or (self.type is None) or (self.type == "") or (self.referenceId is None) or (not isinstance(self.referenceId, IdentityPart)):
                print(f"Equality comparison failed for self: invalid name, type, or referenceId with name={self.name}, type={self.type}, referenceId={self.referenceId}")

                raise ValueError("Invalid name, type, or referenceId for self in equality comparison")
            
            if (other.name is None) or (other.name == "") or (other.type is None) or (other.type == "") or (other.referenceId is None) or (not isinstance(other.referenceId, IdentityPart)):
                print(f"Equality comparison failed for other: invalid name, type, or referenceId with name={other.name}, type={other.type}, referenceId={other.referenceId}")

                raise ValueError("Invalid name, type, or referenceId for other in equality comparison")
            
            # Two ElementBase instances are considered equal if their referenceId attributes are equal
            # The name, type, sourcesId, and description attributes are not considered in the equality comparison
            return self.referenceId == other.referenceId
        
        except ValueError as e:
            print(f"Equality comparison of ElementBase failed: {e}")

            # Return False in case of invalid attributes
            return False

    def __repr__(self) -> str:
        try:
            # Validate that name, type, and referenceId are not empty or None before creating the string representation
            if (self.name is None) or (self.name == "") or (self.type is None) or (self.type == "") or (self.referenceId is None) or (not isinstance(self.referenceId, IdentityPart)):
                print(f"String representation of ElementBase failed, with name={self.name}, type={self.type}, referenceId={self.referenceId}")

                raise ValueError("Invalid name, type, or referenceId for string representation")

            # The string representation of the ElementBase includes the name, type, referenceId, number of sourcesId, and description
            return f"ElementBase(name={self.name}, type={self.type}, referenceId={self.referenceId}, len(sourcesId)={len(self.sourcesId) if self.sourcesId else 0}, description={self.description})"

        except ValueError as e:
            print(f"String representation of ElementBase failed: {e}")

            return "Invalid ElementBase"