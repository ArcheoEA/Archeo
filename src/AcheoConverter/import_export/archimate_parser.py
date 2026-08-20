# import_export/archimate_parser.py

"""
Parser for ArchiMate XML files (versions 3.2 and 4.0).
Supports ISO/IEC 19507:2018 (OpenGroup XMI profile).
"""

from __future__ import annotations
import xml.etree.ElementTree as ET
import re
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
from uuid import uuid4

from pydantic.dataclasses import dataclass
from ..core.element import (
    ArchiElement_v32, ArchiElement_v40,
    ElementTypes_v32, ElementTypes_v40, ArchiElement
)
from ..core.relationship import RelationshipType, ArchiRelationship


@dataclass
class ParseResult:
    """Result of parsing an ArchiMate XML file."""
    model_id: str
    model_name: str
    version: str
    elements: List[ArchiElement]
    relationships: List[Dict[str, Any]]  # For later conversion to ArchiRelationship


def parse_archimate_xml(file_path: Path) -> ParseResult:
    """Parse an ArchiMate XML file (v3.2 or v4.0)."""
    try:
        tree = ET.parse(str(file_path))
        root = tree.getroot()
        
        # Detect version
        version = detect_archimate_version(root)
        
        if version == "3.2":
            return _parse_v32(root, file_path.name)
        elif version == "4.0":
            return _parse_v40(root, file_path.name)
        else:
            raise ValueError(f"Unsupported ArchiMate version: {version}")
    
    except ET.ParseError as e:
        raise RuntimeError(f"Invalid XML syntax in {file_path}: {e}")


def detect_archimate_version(root: ET.Element) -> str:
    """Detect the ArchiMate version from XML namespace or meta tags."""
    ns = root.tag.split("}")[0] + "}" if "}" in root.tag else ""
    
    # Check for version-specific namespaces
    archimate_ns = "{http://www.opengroup.org/xsd/archimate/3.2/}"
    archimate_40_ns = "{http://www.opengroup.org/xsd/archimate/4.0/}"
    
    if ns.startswith(archimate_40_ns):
        return "4.0"
    elif ns.startswith(archimate_ns):
        return "3.2"
    
    # Fallback: check for v4-only elements
    all_elements = list(root.iter()) + [root]
    has_v40_type = any("flow" in elem.tag.lower() for elem in all_elements)
    return "4.0" if has_v40_type else "3.2"


def _parse_element(
    element: ET.Element,
    version: str
) -> Optional[ArchiElement]:
    """Parse a single ArchiMate element."""
    
    local_name = element.tag.split("}")[1] if "}" in element.tag else element.tag
    eid = element.get("id", str(uuid4()))
    name = element.get("name", "")
    description = element.findtext("{*}description")
    folder_id = element.get("{http://www.archimatetool.com#properties}folderId")
    
    # Map XML tags to types
    type_map_v32 = {
        "businessActor": ElementTypes_v32.BusinessActor,
        "applicationComponent": ElementTypes_v32.ApplicationComponent,
        "dataObject": ElementTypes_v32.DataObject,
        # Add all v3.2 types here (full list would be in production)
    }
    
    type_map_v40 = {
        **type_map_v32,
        "goal": ElementTypes_v40.Goal,
        "principle": ElementTypes_v40.Principle,
        # ... rest of v4.0 types
    }
    
    if version == "3.2":
        etype = type_map_v32.get(local_name)
        if not etype:
            return None
        elem_cls = ArchiElement_v32
    else:
        etype = type_map_v40.get(local_name, ElementTypes_v40.BusinessActor)
        elem_cls = ArchiElement_v40
    
    elem_data = {
        "id": eid,
        "name": name or "",
        "description": description,
        "type": etype,
        "folder_id": folder_id
    }
    
    if version == "4.0":
        abstract = element.get("isAbstract", "false").lower() == "true"
        elem_data["is_abstract"] = abstract
    
    return elem_cls(**elem_data)


def _parse_v32(root: ET.Element, model_name: str) -> ParseResult:
    """Parse ArchiMate 3.2 XML structure."""
    elements = []
    
    for element in root.iter():
        if not element.tag.startswith("{"):
            continue
        parsed_elem = _parse_element(element, "3.2")
        if parsed_elem:
            elements.append(parsed_elem)
    
    # Parse relationships (simplified)
    relationships: List[Dict[str, Any]] = []
    
    return ParseResult(
        model_id=str(uuid4()),
        model_name=model_name,
        version="3.2",
        elements=elements,
        relationships=relationships
    )


def _parse_v40(root: ET.Element, model_name: str) -> ParseResult:
    """Parse ArchiMate 4.0 XML structure."""
    elements = []
    
    for element in root.iter():
        if not element.tag.startswith("{"):
            continue
        parsed_elem = _parse_element(element, "4.0")
        if parsed_elem:
            elements.append(parsed_elem)
    
    return ParseResult(
        model_id=str(uuid4()),
        model_name=model_name,
        version="4.0",
        elements=elements,
        relationships=[]
    )
