from dataclasses import dataclass
from typing import Any, List, Optional, Self
from uuid import uuid4
from datetime import datetime

# The IdentityPart class represents a unique identifier for a model, with attributes such as name, type, id, created, and version.
# It includes validation in the constructor and post-initialization method to ensure that the name, type, and id are not empty or None.
# The hash of an IdentityPart is based on its name, type, and id.
@dataclass
class IdentityPart:
    name: str
    type: str
    id: str
    created: datetime
    version: str

    # The __slots__ declaration is used to optimize memory usage by preventing the creation of a __dict__ for each instance of IdentityPart.
    __slots__ = ['name', 'type', 'id', 'created', 'version']

    # The constructor of IdentityPart initializes the name, type, id, created, and version attributes with validation to ensure that name and type are not empty or None.
    def __init__(self,
                pName: str,
                pType: str,
                pId: Optional[str] = None,
                pCreated: Optional[datetime] = None,
                pVersion: Optional[str] = None):
        
        try:
            # Initialize name
            if (pName is None) or (pName == ""):
                raise ValueError("Name cannot be empty")
            else:
                self.name = pName
            
            # Initialize type
            if (pType is None) or (pType == ""):
                raise ValueError("Type cannot be empty")
            else:
                self.type = pType

            # Initialize id
            self.id = pId if pId is not None else "id-" + uuid4().hex
            
            # Initialize created
            self.created = pCreated if pCreated is not None else datetime.now()

            # Initialize version
            self.version = pVersion if pVersion is not None else "0.0.1"

            # Call the post-initialization method to validate the attributes
            self.__post_init__()
        
        except ValueError as e:
            print(f"Initialization of IdentityPart failed: {e}")    

    def __post_init__(self):
        try:
            # Validate that name, type, and id are not empty or None
            if (self.name is None) or (self.name == "") or (self.type is None) or (self.type == "") or (self.id is None) or (self.id == ""):
                print(f"Post-initialization of IdentityPart failed, with name={self.name}, type={self.type}, id={self.id}")

                raise ValueError("Invalid name, type, or id")

        except ValueError as e:
            print(f"Post-initialization of IdentityPart failed: {e}")

    def __hash__(self) -> int:
        try:
            # Validate that name, type, and id are not empty or None before calculating the hash
            if (self.name is None) or (self.name == "") or (self.type is None) or (self.type == "") or (self.id is None) or (self.id == ""):
                print(f"Hash calculation of IdentityPart failed, with name={self.name}, type={self.type}, id={self.id}")

                raise ValueError("Invalid name, type, or id for hashing")
            
            # The hash is based on the name, type, and id of the IdentityPart
            # None of the other attributes (created, version) are included in the hash calculation
            return hash((self.name, self.type, self.id))
            
        except ValueError as e:
            print(f"Hash calculation of IdentityPart failed: {e}")

            # Return a default hash value in case of invalid attributes
            return 0

    def __eq__(self, other: Any) -> bool:
        try:
            # Validate that the other object is an instance of IdentityPart before comparing
            if not isinstance(other, IdentityPart):
                raise ValueError(f"Equality comparison failed: other object is not an instance of IdentityPart")
            
            # Validate that name, type, and id are not empty or None for both instances before comparing
            if (self.name is None) or (self.name == "") or (self.type is None) or (self.type == "") or (self.id is None) or (self.id == ""):
                print(f"Equality comparison failed for self: invalid name, type, or id with name={self.name}, type={self.type}, id={self.id}")

                raise ValueError("Invalid name, type, or id for self in equality comparison")
            
            if (other.name is None) or (other.name == "") or (other.type is None) or (other.type == "") or (other.id is None) or (other.id == ""):
                print(f"Equality comparison failed for other: invalid name, type, or id with name={other.name}, type={other.type}, id={other.id}")

                raise ValueError("Invalid name, type, or id for other in equality comparison")
            
            # Two IdentityPart instances are considered equal if their name, type, and id attributes are equal
            # The created and version attributes are not considered in the equality comparison
            return (self.name, self.type, self.id) == (other.name, other.type, other.id)

        except ValueError as e:
            print(f"Equality comparison failed: {e}")

            return False

    def __repr__(self) -> str:
        try:
            # Validate that name, type, id, created, and version are not empty or None before creating the string representation
            if (self.name is None) or (self.name == "") or (self.type is None) or (self.type == "") or (self.id is None) or (self.id == "") or (self.created is None) or (self.version is None):
                print(f"String representation of IdentityPart failed: invalid attributes with name={self.name}, type={self.type}, id={self.id}, created={self.created}, version={self.version}")

                raise ValueError("Invalid attributes for string representation of IdentityPart")
            
            # The string representation of the IdentityPart includes the name, type, id, created, and version
            return f"IdentityPart(name={self.name}, type={self.type}, id={self.id}, created={self.created}, version={self.version})"

        except ValueError as e:
            print(f"String representation of IdentityPart failed: {e}")

            return "Invalid IdentityPart"