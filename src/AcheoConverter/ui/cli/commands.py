# ui/cli/commands.py

"""
Command implementations for CLI interface.
"""

from pathlib import Path
import logging

from ..core.model_store import ArchiModel
from ..import_export.archimate_parser import parse_archimate_xml
from ..import_export.archimate_writer import ArchiWriter


logger = logging.getLogger(__name__)


def load_model(path: Path) -> "ArchiModel":
    """Load model from XML file."""
    result = parse_archimate_xml(path)
    
    model = ArchiModel(
        id=result.model_id,
        name=result.model_name,
        version=result.version,
        elements=[],
        relationships=[]
    )
    for elem in result.elements:
        model.add_element(elem)
    return model


def export_model(model: "ArchiModel", path: Path):
    """Export model to XML file."""
    writer = ArchiWriter()
    writer.write(model, path)
