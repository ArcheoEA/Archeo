"""Compare router: differences between two models and integration plans.

Endpoints (under ``/api/v1/compare``):

* ``POST /compare``                - compute the full difference report;
* ``POST /compare/integration-plan`` - list the modifications required to
  merge the source model into the base model;
* ``POST /compare/apply``          - apply such a plan to the base model
  (the model in the repository is replaced by the merged copy);
* ``GET  /compare/reports/{id}``   - re-fetch a previously stored report.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends

from ArcheoConverter.api import schemas
from ArcheoConverter.api.deps import get_state
from ArcheoConverter.application import AppState
from ArcheoConverter.exceptions import ModelNotFoundError

router = APIRouter(prefix="/api/v1/compare", tags=["compare"])


def _detail_dict(model, state: AppState) -> dict:
    from ArcheoConverter.api.routers.models import _detail

    return _detail(model, state)


@router.post("", response_model=schemas.CompareResponse, summary="Compare two models")
def compare_models(
    body: schemas.CompareRequest,
    state: AppState = Depends(get_state),
) -> dict:
    """Compare two models (same formalism) and report every difference.

    The result is stored in memory under ``report_id`` so it can be
    re-fetched later with ``GET /compare/reports/{report_id}``.
    """
    base = state.repository.get(body.base_id)
    other = state.repository.get(body.other_id)
    result = state.comparator.compare(base, other, match_by=body.match_by)
    summary = state.summarizer.summarize_comparison(result)
    report_id = f"cmp-{uuid.uuid4().hex[:12]}"
    state.repository.reports.store(report_id, "comparison", result.model_dump())
    return {"report_id": report_id, "result": result, "summary": summary}


@router.post("/integration-plan", response_model=schemas.PlanResponse,
             summary="Integration plan (source -> base)")
def integration_plan(
    body: schemas.PlanRequest,
    state: AppState = Depends(get_state),
) -> dict:
    """List the modifications required to integrate the source model into
    the base model (add / update / optionally remove)."""
    base = state.repository.get(body.base_id)
    source = state.repository.get(body.source_id)
    plan = state.comparator.integration_plan(
        base, source,
        include_removals=body.include_removals,
        match_by=body.match_by,
    )
    report_id = f"plan-{uuid.uuid4().hex[:12]}"
    state.repository.reports.store(report_id, "integration-plan", plan.model_dump())
    return {"report_id": report_id, "plan": plan}


@router.post("/apply", response_model=schemas.ApplyResponse,
             summary="Apply an integration plan to the base model")
def apply_plan(
    body: schemas.PlanRequest,
    state: AppState = Depends(get_state),
) -> dict:
    """Build the plan (same parameters as ``integration-plan``) and apply
    it: the base model in the repository is replaced by the merged model."""
    base = state.repository.get(body.base_id)
    source = state.repository.get(body.source_id)
    plan = state.comparator.integration_plan(
        base, source,
        include_removals=body.include_removals,
        match_by=body.match_by,
    )
    merged, report = state.comparator.apply_plan(base, plan)
    state.repository.replace(merged)
    return {"applied": report, "model": _detail_dict(merged, state)}


@router.get("/reports/{report_id}", summary="Re-fetch a stored comparison/plan report")
def get_report(report_id: str, state: AppState = Depends(get_state)) -> dict:
    """Return a previously stored report (comparison or integration plan).

    Reports are in-memory: they disappear when the server restarts.
    """
    item = state.repository.reports.get(report_id)
    return item


@router.get("/reports", summary="List stored reports")
def list_reports(kind: str | None = None, state: AppState = Depends(get_state)) -> list[dict]:
    """List the stored report ids, optionally filtered by kind."""
    return state.repository.reports.list(kind)
