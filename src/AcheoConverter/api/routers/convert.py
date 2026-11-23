"""Convert router: migrate a model to another formalism/version.

Endpoints (under ``/api/v1/convert``):

* ``GET  /convert/available`` - list the registered conversion rules;
* ``POST /convert``           - run a conversion (optionally a dry run).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from AcheoConverter.api import schemas
from AcheoConverter.api.deps import get_state
from AcheoConverter.application import AppState

router = APIRouter(prefix="/api/v1/convert", tags=["convert"])


@router.get("/available", response_model=list[schemas.ConversionDescriptor],
            summary="Available conversions")
def available_conversions(state: AppState = Depends(get_state)) -> list[dict]:
    """List every registered conversion rule (built-in + custom)."""
    return state.converter.available()


@router.post("", response_model=schemas.ConvertResponse, summary="Convert a model")
def convert_model(
    body: schemas.ConvertRequest,
    state: AppState = Depends(get_state),
) -> dict:
    """Convert a loaded model to a target formalism/version.

    Examples:
    * ArchiMate 3.2 -> 4.0: ``{"model_id": "...", "target_formalism":
      "archimate", "target_version": "4.0"}``;
    * BPMN 2.0 -> ArchiMate 3.2: ``{"model_id": "...", "target_formalism":
      "archimate", "target_version": "3.2"}``.

    With ``dry_run=true`` the report is computed but no new model is
    stored. The converted model is always stored under a new id unless
    ``model_id_new`` is provided.
    """
    model = state.repository.get(body.model_id)
    outcome = state.converter.convert(
        model,
        target_formalism=body.target_formalism,
        target_version=body.target_version,
        repository=state.repository,
        dry_run=body.dry_run,
        name=body.name,
        model_id=body.model_id_new,
        element_policy=body.element_policy,
        relationship_policy=body.relationship_policy,
    )
    return {"report": outcome.report, "model_id": outcome.model_id}
