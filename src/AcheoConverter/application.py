"""Application factory: wires configuration, repository and services into a
FastAPI application.

``create_app()`` is the single entry point used by:

* the ``acheoconverter`` CLI (``python -m AcheoConverter``);
* the ASGI server (``uvicorn AcheoConverter.application:create_app
  --factory``);
* the test-suite (each test gets an isolated application instance).

The factory builds an :class:`AppState` (shared, thread-safe) attached to
``app.state`` and registers the OpenAPI documentation, CORS, exception
handlers and all routers.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from AcheoConverter import __version__
from AcheoConverter.config import AppConfig, load_config
from AcheoConverter.core.repository import ModelRepository
from AcheoConverter.exceptions import AcheoConverterError
from AcheoConverter.formalisms.registry import FormalismRegistry, default_registry
from AcheoConverter.logging_config import setup_logging
from AcheoConverter.services.comparator import ComparatorService
from AcheoConverter.services.converter import (
    ConversionRuleRegistry,
    ConversionService,
    build_builtin_rules,
)
from AcheoConverter.services.exporter import ExportService
from AcheoConverter.services.importer import ImportService
from AcheoConverter.services.search import SearchService
from AcheoConverter.services.summarizer import SummarizerService

logger = logging.getLogger("acheoconverter.application")


@dataclass
class AppState:
    """Shared application state, attached to ``app.state.app_state``."""

    config: AppConfig
    started_at: datetime
    repository: ModelRepository
    formalisms: FormalismRegistry
    conversions: ConversionRuleRegistry
    importer: ImportService
    search: SearchService
    converter: ConversionService
    comparator: ComparatorService
    summarizer: SummarizerService
    exporter: ExportService


def build_state(config: AppConfig) -> AppState:
    """Build the shared state (repository + registries + services)."""
    repository = ModelRepository()
    formalisms = default_registry()
    conversions = ConversionRuleRegistry()
    for rule in build_builtin_rules():
        conversions.register(rule)

    importer = ImportService(
        formalisms,
        max_upload_bytes=config.limits.max_upload_mb * 1024 * 1024,
    )
    search = SearchService(
        max_results=config.limits.max_search_results,
        max_depth=config.limits.max_navigation_depth,
        max_nodes=config.limits.max_graph_nodes,
    )
    converter = ConversionService(conversions)
    comparator = ComparatorService(default_match_by=config.comparison.match_by)
    summarizer = SummarizerService()
    exporter = ExportService(converter)
    return AppState(
        config=config,
        started_at=datetime.now(timezone.utc),
        repository=repository,
        formalisms=formalisms,
        conversions=conversions,
        importer=importer,
        search=search,
        converter=converter,
        comparator=comparator,
        summarizer=summarizer,
        exporter=exporter,
    )


def create_app(config: AppConfig | None = None, *, setup_app_logging: bool = True) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        config: application configuration; loaded from the default sources
            (``config/app.json`` / environment) when omitted.
        setup_app_logging: configure the logging system (disable in tests
            to avoid duplicate handlers).

    Returns:
        The ready-to-serve :class:`FastAPI` instance.
    """
    if config is None:
        config = load_config()
    if setup_app_logging:
        setup_logging(config.logging, force=True)

    state = build_state(config)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        logger.info(
            "%s %s starting (formalisms: %s, conversions: %d)",
            config.app_name, config.version,
            ", ".join(state.formalisms.formalisms()),
            len(state.conversions.all()),
        )
        yield
        logger.info("%s shutting down (models in memory: %d)",
                    config.app_name, len(state.repository))

    app = FastAPI(
        title="AcheoConverter API",
        version=__version__,
        description=(
            "AcheoConverter imports, stores in memory, searches, visualizes, "
            "converts, compares and exports enterprise architecture models "
            "(ArchiMate 3.2 / 4.0, BPMN 2.0, UML, SysML). "
            "Interactive documentation: /docs (Swagger UI) and /redoc."
        ),
        lifespan=lifespan,
    )
    app.state.app_state = state

    if config.server.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=config.server.cors_origins,
            allow_credentials=False,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # --- exception handling ------------------------------------------- #
    @app.exception_handler(AcheoConverterError)
    async def domain_error_handler(_: Request, exc: AcheoConverterError) -> JSONResponse:
        logger.warning("domain error: %s (%s)", exc.message, exc.code)
        return JSONResponse(status_code=exc.http_status, content=exc.to_payload())

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "detail": "Request validation failed.",
                "code": "validation_error",
                "details": [str(err) for err in exc.errors()][:10],
            },
        )

    # --- routers -------------------------------------------------------- #
    # Imported lazily: the routers import AppState from this module, so a
    # module-level import would create a circular import.
    from AcheoConverter.api.routers import admin, compare, convert, meta, models, ui

    app.include_router(meta.router)
    app.include_router(models.router)
    app.include_router(convert.router)
    app.include_router(compare.router)
    app.include_router(admin.router)
    app.include_router(ui.router)

    @app.get("/health", tags=["meta"], summary="Liveness probe")
    def health() -> dict:
        """Simple liveness endpoint for load balancers / orchestration."""
        return {"status": "ok", "app": config.app_name, "version": __version__}

    return app
