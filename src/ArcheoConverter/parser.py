"""Streaming XML parser for ArchiMate 3.2/4.0 models."""

import xml.etree.ElementTree as ET

from typing import Generator

from .models import ArchiMateModel, ArchiMateElement, ArchiMateRelationship, ArchiMateView
from .logger_setup import get_logger

logger = get_logger(__name__)

ARCHIMATE_NS = {
    "3.2": "http://www.opengroup.org/xsd/archimate/3.2",
    "4.0": "http://www.opengroup.org/xsd/archimate/4.0"
}

def _strip_ns(tag: str) -> str:
    return tag.split("}")[-1] if "}" in tag else tag

def parse_archimate_stream(file_path: str) -> ArchiMateModel:
    """Parse ArchiMate XML using streaming for large file support."""
    logger.info(f"Starting parse of {file_path}")
    model = ArchiMateModel(id="model-001")
    try:
        tree = ET.iterparse(file_path, events=("start", "end"))
        for event, elem in tree:
            tag = _strip_ns(elem.tag)
            if event == "start" and tag == "archimate":
                model.version = elem.get("version", "3.2")
                model.id = elem.get("id", "model-001")
                model.name = elem.get("name", "Untitled Model")
            elif event == "end":
                if tag == "element":
                    _parse_element(elem, model)
                elif tag == "relationship":
                    _parse_relationship(elem, model)
                elif tag == "view":
                    _parse_view(elem, model)
                elif tag == "folder":
                    model.folders[elem.get("id")] = elem.get("name", "Folder")
                elif tag == "property":
                    if tag == "property":
                        model.metadata[elem.get("name")] = elem.text or ""
                elem.clear()  # Free memory
        logger.info("Parse completed successfully")
        return model
    except Exception as e:
        logger.error(f"Parse failed: {e}")
        raise RuntimeError(f"Failed to parse ArchiMate model: {e}")

def _parse_element(elem: ET.Element, model: ArchiMateModel) -> None:
    model.elements[elem.get("id")] = ArchiMateElement(
        id=elem.get("id"),
        type=elem.get("type"),
        name=elem.get("name", ""),
        description=elem.get("description", ""),
        folder_id=elem.get("folder"),
        properties={p.get("name"): p.text for p in elem.findall(".//property")}
    )

def _parse_relationship(elem: ET.Element, model: ArchiMateModel) -> None:
    model.relationships[elem.get("id")] = ArchiMateRelationship(
        id=elem.get("id"),
        type=elem.get("type"),
        source_id=elem.get("source"),
        target_id=elem.get("target"),
        properties={p.get("name"): p.text for p in elem.findall(".//property")}
    )

def _parse_view(elem: ET.Element, model: ArchiMateModel) -> None:
    view = ArchiMateView(
        id=elem.get("id"),
        name=elem.get("name", ""),
        element_ids=[e.get("href") for e in elem.findall(".//elementReference")],
        relationship_ids=[r.get("href") for r in elem.findall(".//relationshipReference")]
    )
    model.views[view.id] = view
