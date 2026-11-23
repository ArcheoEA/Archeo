"""Meta endpoint: application identity, capabilities and documentation links."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ArcheoConverter.api.deps import get_state
from ArcheoConverter.api.schemas import ConversionDescriptor, FormalismDescriptor, MetaResponse
from ArcheoConverter.application import AppState

router = APIRouter(prefix="/api/v1", tags=["meta"])


@router.get(
    "/meta",
    response_model=MetaResponse,
    summary="Application identity and capabilities",
)
def meta(state: AppState = Depends(get_state)) -> MetaResponse:
    """Return the application name/version, supported formalisms, available
    conversions and the OpenAPI documentation URLs.

    This is the first endpoint a client (Insomnia, Bruno, ApiDog, the UI)
    should call to discover what the server offers.
    """
    return MetaResponse(
        app=state.config.app_name,
        version=state.config.version,
        description=(
            "Import, convert, compare and export enterprise architecture "
            "models (ArchiMate 3.2/4.0, BPMN 2.0, UML, SysML)."
        ),
        formalisms=[
            FormalismDescriptor(
                formalism=info.formalism,
                version=info.version,
                description=info.description,
                importable=info.importable,
                exportable=info.exportable,
                default_version=info.default_version,
            )
            for info in state.formalisms.infos()
        ],
        conversions=[
            ConversionDescriptor(
                id=rule["id"],
                source_formalism=rule["source_formalism"],
                source_versions=rule["source_versions"],
                target_formalism=rule["target_formalism"],
                target_versions=rule["target_versions"],
                description=rule["description"],
            )
            for rule in state.converter.available()
        ],
        ui=state.config.ui_enabled,
        openapi="/openapi.json",
        docs="/docs",
    )
