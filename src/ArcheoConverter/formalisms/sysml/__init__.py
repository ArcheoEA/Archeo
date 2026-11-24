"""SysML formalism support via XMI (dedicated import extension)."""

from ArcheoConverter.formalisms.sysml.mapper import (
    DEFAULT_SYSML_ELEMENT_MAP,
    DEFAULT_SYSML_RELATIONSHIP_MAP,
    DEFAULT_SYSML_ELEMENT_STEREOTYPES,
)
from ArcheoConverter.formalisms.sysml.parser import SysmlHandler

__all__ = [
    "SysmlHandler",
    "DEFAULT_SYSML_ELEMENT_STEREOTYPES",
    "DEFAULT_SYSML_ELEMENT_MAP",
    "DEFAULT_SYSML_RELATIONSHIP_MAP",
]
