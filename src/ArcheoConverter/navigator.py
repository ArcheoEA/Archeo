"""Search, navigation, and tree building functionality."""

from typing import Optional

from .models import ArchiMateModel
from .logger_setup import get_logger

logger = get_logger(__name__)

def search_elements(model: ArchiMateModel, query: str, field: str = "name") -> list[str]:
    """Search elements by field and return matching IDs."""
    logger.info(f"Searching {field} for '{query}'")
    results = []
    for eid, elem in model.elements.items():
        val = getattr(elem, field, "")
        if isinstance(val, str) and query.lower() in val.lower():
            results.append(eid)
    return results

def get_folder_tree(model: ArchiMateModel) -> dict[str, list[str]]:
    """Build a folder -> element IDs tree."""
    logger.info("Building folder tree")
    tree: dict[str, list[str]] = {}
    for eid, elem in model.elements.items():
        fid = elem.folder_id or "root"
        tree.setdefault(fid, []).append(eid)
    return tree

def get_view_elements(model: ArchiMateModel, view_id: str) -> list[str]:
    """Return element IDs contained in a specific view."""
    view = model.views.get(view_id)
    return view.element_ids if view else []

def filter_by_type(model: ArchiMateModel, elem_type: str) -> list[str]:
    """Filter elements by ArchiMate type."""
    return [eid for eid, elem in model.elements.items() if elem.type == elem_type]
