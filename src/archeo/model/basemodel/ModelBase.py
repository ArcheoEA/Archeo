from dataclasses import dataclass
from typing import Any, List, Optional, Self
from uuid import uuid4
from datetime import datetime

# The ModelBase class represents a model with attributes such as name, formalism, version, customization, and description.
# It includes validation in the constructor and post-initialization method to ensure that the name and formalism are not empty or None.
@dataclass ()
class ModelBase:
    name: str
    formalism: str
    version: str | None
    customization: str | None
    description: Optional[str] | None

    # The __slots__ declaration is used to optimize memory usage by preventing the creation of a __dict__ for each instance of ElementBase.
    __slots__ = ['name', 'formalism', 'version', 'customization', 'description']

    # The constructor of ElementBase initializes the name, formalism, version, customization, and description attributes with validation to ensure that name, and formalism are not empty or None.
    def __init__(self,
                pName: str,
                pFormalism: str,
                pVersion: Optional[str] = None,
                pCustomization: Optional[str] = None,
                pDescription: Optional[str] = None):

        try:
            # Initialize name
            if (pName is None) or (pName == ""):
                raise ValueError("Name cannot be empty")
            else:
                self.name = pName

            # Initialize formalism
            if (pFormalism is None) or (pFormalism == ""):
                raise ValueError("Formalism cannot be empty")
            else:
                self.formalism = pFormalism

            # Initialize version
            self.version = pVersion if pVersion is not None else "0.0.1"

            # Initialize customization
            self.customization = pCustomization

            # Initialize description
            self.description = pDescription

            # Call the post-initialization method to validate the attributes
            self.__post_init__()

        except ValueError as e:
            print(f"Initialization of ModelBase failed: {e}")

    def __post_init__(self):
        try:
            # Validate that name, formalism, and version are not empty or None
            if (self.name is None) or (self.name == "") or (self.formalism is None) or (self.formalism == "") or (self.version is None) or (self.version == ""):
                print(f"Post-initialization of ModelBase failed, with name={self.name}, formalism={self.formalism} and version={self.version}")

                raise ValueError("Invalid name")

        except ValueError as e:
            print(f"Post-initialization of ModelBase failed: {e}")

    def __hash__(self) -> int:
        try:
            # Validate that name, formalism, and version are not empty or None
            if (self.name is None) or (self.name == "") or (self.formalism is None) or (self.formalism == "") or (self.version is None) or (self.version == ""):
                print(f"Hash calculation of ModelBase failed, with name={self.name}, formalism={self.formalism} and version={self.version}")

                raise ValueError("Invalid name, formalism or version for hashing")
            
            # The hash is based on the name, formalism, and version of ModelBase
            # None of the other attributes are included in the hash calculation
            return hash((self.name, self.formalism, self.version))
            
        except ValueError as e:
            print(f"Hash calculation of ModelBase failed: {e}")

            # Return a default hash value in case of invalid attributes
            return 0

    def __eq__(self, other: Any) -> bool:
        try:
            # Validate that the other object is an instance of ModelBase before comparing
            if not isinstance(other, ModelBase):
                print(f"Equality comparison of ModelBase failed: Other object is not an instance of ModelBase")

                raise ValueError("Equality comparison failed: Other object is not an instance of ModelBase")

            # Validate that name, formalism, and version are not empty or None, for both instances before comparing
            if (self.name is None) or (self.name == "") or (self.formalism is None) or (self.formalism == "") or (self.version is None) or (self.version == ""):
                print(f"Equality comparison failed for self: Invalid name with name={self.name}, formalism={self.formalism} and version={self.version}")

                raise ValueError("Invalid name for self in equality comparison")
            
            if (other.name is None) or (other.name == "") or (other.formalism is None) or (other.formalism == "") or (other.version is None) or (other.version == ""):
                print(f"Equality comparison failed for other: Invalid name with name={other.name}, formalism={other.formalism} and version={other.version}")

                raise ValueError("Invalid name for other in equality comparison")   
            
            # Two ModelBase instances are considered equal if their hash (based on name, formalism, and version attributes) are equal
            # All of the other attributes are not considered in the equality comparison
            return self.__hash__() == other.__hash__()
        
        except ValueError as e:
            print(f"Equality comparison of ModelBase failed: {e}")

            # Return False in case of invalid attributes
            return False

    def __repr__(self) -> str:
        try:
            # Validate that name, formalism, and version are not empty or None before creating the string representation
            if (self.name is None) or (self.name == "") or (self.formalism is None) or (self.formalism == "") or (self.version is None) or (self.version == ""):
                print(f"String representation of ModelBase failed, with name={self.name}, formalism={self.formalism} and version={self.version}")

                raise ValueError("Invalid name for string representation")

            # The string representation of the ModelBase includes all attributes
            return f"ModelBase(name={self.name}, formalism={self.formalism}, version={self.version}, customization={self.customization}, description={self.description})"

        except ValueError as e:
            print(f"String representation of ModelBase failed: {e}")

            return "Invalid ModelBase"