"""SysML formalism support via XMI (dedicated import extension)."""

from ArcheoConverter.formalisms.sysml.mapper import (
    DEFAULT_SYSML_ELEMENT_MAP,
    DEFAULT_SYSML_RELATIONSHIP_MAP,
    SYSML_ELEMENT_TYPES,
)
from ArcheoConverter.formalisms.sysml.parser import SysmlHandler

__all__ = [
    "SysmlHandler",
    "SYSML_ELEMENT_TYPES",
    "DEFAULT_SYSML_ELEMENT_MAP",
    "DEFAULT_SYSML_RELATIONSHIP_MAP",
]
