"""UML formalism support via XMI (dedicated import extension)."""

from AcheoConverter.formalisms.uml.mapper import (
    DEFAULT_UML_ELEMENT_MAP,
    DEFAULT_UML_RELATIONSHIP_MAP,
    UML_ELEMENT_TYPES,
)
from AcheoConverter.formalisms.uml.parser import UmlHandler

__all__ = [
    "UmlHandler",
    "UML_ELEMENT_TYPES",
    "DEFAULT_UML_ELEMENT_MAP",
    "DEFAULT_UML_RELATIONSHIP_MAP",
]
