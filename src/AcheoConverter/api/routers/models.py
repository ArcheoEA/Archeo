"""Models router: import, listing, navigation, visualization and export.

Endpoints (all under ``/api/v1``):

* ``POST /models``                 - import a model file (multipart upload);
* ``POST /models/import``          - import a model from a JSON body;
* ``GET  /models``                 - list loaded models;
* ``GET  /models/{id}``            - model detail + summary;
* ``DELETE /models/{id}``          - remove a model;
* ``GET  /models/{id}/elements``   - search elements (q, type, stereotype,
  tag, folder, property, pagination);
* ``GET  /models/{id}/elements/{element_id}`` - element detail + links;
* ``GET  /models/{id}/relationships``          - list relationships;
* ``GET  /models/{id}/folders``                - folder tree;
* ``GET  /models/{id}/folders/{folder_id}``    - folder content;
* ``GET  /models/{id}/graph``                  - graph payload (nodes/edges)
  for visualization;
* ``GET  /models/{id}/summary``                - structured summary;
* ``POST /models/{id}/export``                 - export to Model Exchange XML
  (full / partial / filtered, target version selectable).
"""

from __future__ import annotations

import base64
import binascii
import json
from typing import Any

from fastapi import APIRouter, Depends, File, Form, Path, Query, Response, UploadFile
from starlette.responses import JSONResponse

from AcheoConverter.api.deps import get_state
from AcheoConverter.api import schemas
from AcheoConverter.core.models import Model
from AcheoConverter.exceptions import ModelNotFoundError
from AcheoConverter.services.search import GraphPayload, SearchPage
from AcheoConverter.services.summarizer import ModelSummary
from AcheoConverter.application import AppState

router = APIRouter(prefix="/api/v1/models", tags=["models"])


# --------------------------------------------------------------------- #
# Import
# --------------------------------------------------------------------- #
@router.post(
    "",
    status_code=201,
    summary="Import a model file (multipart upload)",
)
async def import_model(
    file: UploadFile = File(..., description="Model file (.archimate, .bpmn, .xmi, ...)"),
    model_id: str | None = Form(default=None, description="Explicit model id"),
    name: str | None = Form(default=None, description="Model name override"),
    formalism: str | None = Form(default=None, description="Force a formalism"),
    version: str | None = Form(default=None, description="Force a formalism version"),
    overwrite: bool = Form(default=False),
    state: AppState = Depends(get_state),
) -> dict[str, Any]:
    """Import a model file into the in-memory repository.

    The formalism and version are auto-detected when not provided.
    """
    content = await file.read()
    result = state.importer.import_content(
        content,
        repository=state.repository,
        filename=file.filename,
        model_id=model_id,
        name=name,
        formalism=formalism,
        version=version,
        overwrite=overwrite,
    )
    return result.model_dump()


@router.post(
    "/import",
    status_code=201,
    response_model=schemas.ImportResult,
    summary="Import a model from a JSON body",
)
def import_model_json(
    body: schemas.ImportJsonRequest,
    state: AppState = Depends(get_state),
) -> dict[str, Any]:
    """Import a model from a JSON body (``content`` or ``content_base64``).

    Handy for scripted imports and API testing (Insomnia/Bruno/ApiDog)
    where file uploads are awkward.
    """
    if body.content and body.content_base64:
        return JSONResponse(
            status_code=422,
            content={"detail": "Provide either 'content' or 'content_base64', not both."},
        )
    content: bytes
    if body.content_base64:
        try:
            content = base64.b64decode(body.content_base64, validate=True)
        except (binascii.Error, ValueError) as exc:
            return JSONResponse(
                status_code=422,
                content={"detail": f"Invalid base64 content: {exc}"},
            )
    elif body.content:
        content = body.content.encode("utf-8")
    else:
        return JSONResponse(
            status_code=422,
            content={"detail": "Provide 'content' or 'content_base64'."},
        )

    result = state.importer.import_content(
        content,
        repository=state.repository,
        filename=body.filename,
        model_id=body.model_id,
        name=body.name,
        formalism=body.formalism,
        version=body.version,
        overwrite=body.overwrite,
    )
    return result.model_dump()


# --------------------------------------------------------------------- #
# CRUD
# --------------------------------------------------------------------- #
@router.get("", summary="List loaded models")
def list_models(state: AppState = Depends(get_state)) -> list[dict[str, Any]]:
    """Return every model currently in memory (with counts)."""
    return [
        {
            "model_id": model.model_id,
            "name": model.metadata.name,
            "formalism": model.metadata.formalism,
            "version": model.metadata.version,
            "source_file": model.metadata.source_file,
            "imported_at": model.metadata.imported_at.isoformat(),
            "element_count": len(model.elements),
            "relationship_count": len(model.relationships),
            "folder_count": len(model.folders),
        }
        for model in state.repository.list()
    ]


def _detail(model: Model, state: AppState) -> dict[str, Any]:
    """Build the model detail payload (metadata + structured summary)."""
    summary: ModelSummary = state.summarizer.summarize(model)
    return {
        "model_id": model.model_id,
        "name": model.metadata.name,
        "formalism": model.metadata.formalism,
        "version": model.metadata.version,
        "source_file": model.metadata.source_file,
        "imported_at": model.metadata.imported_at.isoformat(),
        "notes": model.metadata.notes,
        "element_count": len(model.elements),
        "relationship_count": len(model.relationships),
        "folder_count": len(model.folders),
        "summary": summary.model_dump(),
    }


@router.get("/{model_id}", summary="Model detail + summary")
def get_model(model_id: str, state: AppState = Depends(get_state)) -> dict[str, Any]:
    """Return the detail of one loaded model."""
    return _detail(state.repository.get(model_id), state)


@router.delete(
    "/{model_id}",
    status_code=204,
    summary="Remove a model from memory",
)
def delete_model(model_id: str, state: AppState = Depends(get_state)) -> None:
    """Delete a loaded model (and its reports are kept)."""
    if not state.repository.remove(model_id):
        raise ModelNotFoundError(f"Model '{model_id}' is not loaded.")


# --------------------------------------------------------------------- #
# Elements (search / navigation)
# --------------------------------------------------------------------- #
@router.get("/{model_id}/elements", response_model=SearchPage, summary="Search elements")
def search_elements(
    model_id: str,
    state: AppState = Depends(get_state),
    q: str | None = Query(default=None, description="Free text (name/type/stereotype/tag)"),
    types: list[str] = Query(default_factory=list, description="Filter by element type(s)"),
    stereotypes: list[str] = Query(default_factory=list, description="Filter by stereotype(s)"),
    tags: list[str] = Query(default_factory=list, description="Filter by tag(s)"),
    folder: str | None = Query(default=None, description="Filter by folder id"),
    property_key: str | None = Query(default=None, description="Required extended property"),
    property_value: str | None = Query(default=None, description="Extended property value"),
    limit: int = Query(default=50, ge=1),
    offset: int = Query(default=0, ge=0),
) -> SearchPage:
    """Search the elements of a model (AND-combined filters, ranked)."""
    model = state.repository.get(model_id)
    return state.search.search(
        model,
        query=q,
        types=schemas.explode_csv(types) or None,
        stereotypes=schemas.explode_csv(stereotypes) or None,
        tags=schemas.explode_csv(tags) or None,
        folder_id=folder,
        property_key=property_key,
        property_value=property_value,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{model_id}/elements/{element_id}",
    response_model=schemas.ElementDetail,
    summary="Element detail with its relationships",
)
def get_element(
    model_id: str,
    element_id: str,
    state: AppState = Depends(get_state),
) -> dict[str, Any]:
    """Return one element plus its inbound/outbound relationships."""
    model = state.repository.get(model_id)
    element = model.elements.get(element_id)
    if element is None:
        raise ModelNotFoundError(f"Element '{element_id}' was not found in model '{model_id}'.")
    inbound = [r for r in model.relationships.values() if r.target == element_id]
    outbound = [r for r in model.relationships.values() if r.source == element_id]
    return {"element": element, "inbound": inbound, "outbound": outbound}


@router.get(
    "/{model_id}/relationships",
    response_model=schemas.RelationshipPage,
    summary="List relationships",
)
def list_relationships(
    model_id: str,
    state: AppState = Depends(get_state),
    type: list[str] = Query(default_factory=list, description="Filter by relationship type(s)"),
    source: str | None = Query(default=None, description="Filter by source element id"),
    target: str | None = Query(default=None, description="Filter by target element id"),
    limit: int = Query(default=100, ge=1),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    """List the relationships of a model with optional filters."""
    model = state.repository.get(model_id)
    types_set = {t.lower() for t in schemas.explode_csv(type)} or None
    items = [
        rel for rel in model.relationships.values()
        if (types_set is None or rel.type.lower() in types_set)
        and (source is None or rel.source == source)
        and (target is None or rel.target == target)
    ]
    items.sort(key=lambda r: r.id)
    return {
        "total": len(items),
        "offset": offset,
        "limit": limit,
        "items": items[offset : offset + limit],
    }


# --------------------------------------------------------------------- #
# Folders / views
# --------------------------------------------------------------------- #
def _folder_tree(model: Model, folder_id: str | None) -> list[dict[str, Any]]:
    """Build the recursive folder tree (with a cycle guard)."""
    children_by_parent: dict[str | None, list[str]] = {}
    for fid, folder in model.folders.items():
        children_by_parent.setdefault(folder.parent_id, []).append(fid)

    def build(fid: str, visited: set[str]) -> dict[str, Any]:
        folder = model.folders[fid]
        visited.add(fid)
        children = [
            build(child, visited)
            for child in sorted(
                children_by_parent.get(fid, []),
                key=lambda c: model.folders[c].name.lower(),
            )
            if child not in visited
        ]
        return {
            "id": fid,
            "name": folder.name,
            "kind": folder.kind,
            "description": folder.description,
            "parent_id": folder.parent_id,
            "element_count": len(folder.element_ids),
            "children": children,
        }

    return [
        build(fid, set())
        for fid in sorted(
            children_by_parent.get(folder_id, []),
            key=lambda c: model.folders[c].name.lower(),
        )
    ]


@router.get("/{model_id}/folders", summary="Folder / view tree")
def list_folders(model_id: str, state: AppState = Depends(get_state)) -> dict[str, Any]:
    """Return the full folder tree of a model (views + folder structure)."""
    model = state.repository.get(model_id)
    return {"tree": _folder_tree(model, None)}


@router.get(
    "/{model_id}/folders/{folder_id}",
    response_model=schemas.FolderDetail,
    summary="Folder content",
)
def get_folder(
    model_id: str,
    folder_id: str,
    state: AppState = Depends(get_state),
) -> dict[str, Any]:
    """Return one folder with its elements and contained relationships."""
    model = state.repository.get(model_id)
    folder = model.folders.get(folder_id)
    if folder is None:
        raise ModelNotFoundError(f"Folder '{folder_id}' was not found in model '{model_id}'.")
    element_ids = set(folder.element_ids)
    relationships = [
        rel for rel in model.relationships.values()
        if rel.source in element_ids and rel.target in element_ids
    ]
    return {
        "id": folder.id,
        "name": folder.name,
        "kind": folder.kind,
        "description": folder.description,
        "parent_id": folder.parent_id,
        "elements": [model.elements[eid] for eid in folder.element_ids if eid in model.elements],
        "relationships": relationships,
    }


# --------------------------------------------------------------------- #
# Graph (visualization payload)
# --------------------------------------------------------------------- #
@router.get(
    "/{model_id}/graph",
    response_model=GraphPayload,
    summary="Graph payload for visualization",
)
def graph(
    model_id: str,
    state: AppState = Depends(get_state),
    from_element: str | None = Query(
        default=None, alias="from", description="Root element id (neighborhood)"
    ),
    folder: str | None = Query(default=None, description="Folder id (full folder graph)"),
    depth: int = Query(default=2, ge=1, description="Neighborhood depth"),
    types: list[str] = Query(default_factory=list, description="Whole-model graph type filter"),
) -> GraphPayload:
    """Return nodes/edges for the UI graph renderer.

    Priority: ``from`` (neighborhood) > ``folder`` (folder graph) > whole
    model. The node limit is enforced by the engine.
    """
    model = state.repository.get(model_id)
    if from_element:
        return state.search.neighbors(model, from_element, depth=depth)
    if folder:
        return state.search.folder_graph(model, folder)
    return state.search.model_graph(model, element_types=schemas.explode_csv(types) or None)


# --------------------------------------------------------------------- #
# Summary
# --------------------------------------------------------------------- #
@router.get(
    "/{model_id}/summary",
    response_model=ModelSummary,
    summary="Structured model summary",
)
def summary(model_id: str, state: AppState = Depends(get_state)) -> ModelSummary:
    """Return the structured summary (counts, histograms, integrity)."""
    return state.summarizer.summarize(state.repository.get(model_id))


@router.get(
    "/{model_id}/summary/markdown",
    response_class=Response,
    summary="Markdown model summary",
)
def summary_markdown(model_id: str, state: AppState = Depends(get_state)) -> Response:
    """Return the model summary rendered as Markdown."""
    model = state.repository.get(model_id)
    text = state.summarizer.render_markdown(state.summarizer.summarize(model))
    return Response(content=text, media_type="text/markdown; charset=utf-8")


# --------------------------------------------------------------------- #
# Export
# --------------------------------------------------------------------- #
@router.post("/{model_id}/export", summary="Export to ArchiMate Model Exchange XML")
def export_model(
    model_id: str,
    body: schemas.ExportRequest,
    state: AppState = Depends(get_state),
    format: str = Query(default="xml", description="xml | json"),
) -> Any:
    """Export a model (full / partial / filtered) to the standard XML format.

    Returns the XML document directly (``format=xml``, default) or a JSON
    envelope with the XML text + report (``format=json``).
    """
    model = state.repository.get(model_id)
    xml_bytes, report = state.exporter.export(model, body)
    if format == "json":
        from AcheoConverter.api.schemas import ExportJsonResponse

        return ExportJsonResponse(
            report=report,
            xml=xml_bytes.decode("utf-8"),
            markdown=state.summarizer.render_markdown(state.summarizer.summarize(model)),
        )
    filename = f"{model.metadata.name.replace(' ', '_') or model.model_id}.archimate"
    return Response(
        content=xml_bytes,
        media_type="application/xml",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Export-Report": json.dumps(report.model_dump(), default=str),
        },
    )
