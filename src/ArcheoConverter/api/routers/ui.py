"""UI router: serves the minimal single-page user interface.

The UI is a static bundle (HTML + JS + CSS) that talks exclusively to the
JSON API of this application - there is no server-side templating. It can
be disabled with ``ui_enabled=false`` in the configuration.

Routes:

* ``GET /``          - the application shell (index.html);
* ``GET /ui/{file}`` - static assets (app.js, style.css, index.html).
"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from starlette.responses import FileResponse

from ArcheoConverter.api.deps import get_state
from ArcheoConverter.application import AppState

logger = logging.getLogger("archeoconverter.ui")

router = APIRouter(tags=["ui"])

#: Directory of the static UI assets (inside the installed package).
UI_DIR = Path(__file__).resolve().parent.parent.parent / "ui"

_MEDIA_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
}


def _static(filename: str) -> FileResponse:
    """Resolve a static file name safely (no path traversal)."""
    safe = Path(filename).name  # strip any directory components
    path = UI_DIR / safe
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"Static file '{safe}' not found.")
    media_type = _MEDIA_TYPES.get(path.suffix, "application/octet-stream")
    return FileResponse(path, media_type=media_type)


@router.get("/", include_in_schema=False)
def index(state: AppState = Depends(get_state)) -> FileResponse:
    """Serve the UI shell (disabled when ``ui_enabled`` is false)."""
    if not state.config.ui_enabled:
        raise HTTPException(status_code=404, detail="The UI is disabled (ui_enabled=false).")
    return _static("index.html")


@router.get("/ui/{filename}", include_in_schema=False)
def static_file(filename: str, state: AppState = Depends(get_state)) -> FileResponse:
    """Serve one static UI asset."""
    if not state.config.ui_enabled:
        raise HTTPException(status_code=404, detail="The UI is disabled (ui_enabled=false).")
    return _static(filename)
