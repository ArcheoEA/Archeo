"""UML formalism support via XMI (dedicated import extension)."""

from ArcheoConverter.formalisms.uml.mapper import (
    DEFAULT_UML_ELEMENT_MAP,
    DEFAULT_UML_RELATIONSHIP_MAP,
    DEFAULT_UML_ELEMENT_STEREOTYPES,
)
from ArcheoConverter.formalisms.uml.parser import UmlHandler

__all__ = [
    "UmlHandler",
    "DEFAULT_UML_ELEMENT_STEREOTYPES",
    "DEFAULT_UML_ELEMENT_MAP",
    "DEFAULT_UML_RELATIONSHIP_MAP",
]
