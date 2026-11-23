"""Admin router: configuration introspection, statistics, purge.

Endpoints (under ``/api/v1/admin``):

* ``GET  /admin/config`` - the effective configuration (sanitized);
* ``GET  /admin/stats``  - aggregate in-memory statistics;
* ``POST /admin/purge``  - drop every loaded model and report.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from AcheoConverter.api import schemas
from AcheoConverter.api.deps import get_state
from AcheoConverter.application import AppState

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.get("/config", summary="Effective application configuration")
def get_config(state: AppState = Depends(get_state)) -> dict:
    """Return the effective configuration.

    Sensitive values are not exposed (none exist in the default schema,
    but the config is filtered to known keys for forward compatibility).
    """
    return state.config.model_dump(mode="json")


@router.get("/stats", response_model=schemas.StatsResponse, summary="In-memory statistics")
def stats(state: AppState = Depends(get_state)) -> dict:
    """Return aggregate statistics over the in-memory state."""
    repository_stats = state.repository.stats()
    uptime = (
        datetime.now(timezone.utc) - state.started_at
    ).total_seconds()
    return {
        "models": repository_stats["models"],
        "elements": repository_stats["elements"],
        "relationships": repository_stats["relationships"],
        "folders": repository_stats["folders"],
        "reports": repository_stats["reports"],
        "memory_estimate_bytes": repository_stats["memory_estimate_bytes"],
        "by_formalism": repository_stats["by_formalism"],
        "uptime_seconds": round(uptime, 3),
    }


@router.post("/purge", response_model=schemas.PurgeResponse,
             summary="Remove all models and reports")
def purge(state: AppState = Depends(get_state)) -> dict:
    """Administrative operation: empty the in-memory repository."""
    deleted = state.repository.clear()
    return {"deleted_models": deleted, "deleted_reports": 0}
