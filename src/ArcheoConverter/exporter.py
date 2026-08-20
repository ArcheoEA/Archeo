"""Export in-memory model to OpenGroup XML format."""

import xml.etree.ElementTree as ET

from xml.dom import minidom

from .models import ArchiMateModel
from .logger_setup import get_logger

logger = get_logger(__name__)

def export_to_xml(model: ArchiMateModel, file_path: str) -> None:
    """Serialize model to ArchiMate OpenGroup XML."""
    logger.info(f"Exporting model to {file_path}")
    root = ET.Element("archimate", {
        "xmlns": f"http://www.opengroup.org/xsd/archimate/{model.version}",
        "version": model.version,
        "id": model.id,
        "name": model.name
    })

    for elem in model.elements.values():
        e = ET.SubElement(root, "element", {
            "id": elem.id, "type": elem.type, "name": elem.name,
            "description": elem.description, "folder": elem.folder_id or ""
        })
        for k, v in elem.properties.items():
            ET.SubElement(e, "property", {"name": k}).text = v

    for rel in model.relationships.values():
        ET.SubElement(root, "relationship", {
            "id": rel.id, "type": rel.type,
            "source": rel.source_id, "target": rel.target_id
        })

    for view in model.views.values():
        v = ET.SubElement(root, "view", {"id": view.id, "name": view.name})
        for eid in view.element_ids:
            ET.SubElement(v, "elementReference", {"href": eid})
        for rid in view.relationship_ids:
            ET.SubElement(v, "relationshipReference", {"href": rid})

    tree = ET.ElementTree(root)
    pretty_xml = minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ")
    with open(file_path, "w") as f:
        f.write(pretty_xml)
    logger.info("Export completed successfully")
