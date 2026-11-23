"""Request / response schemas of the ArcheoConverter HTTP API.

These Pydantic models are the OpenAPI contract: FastAPI generates
``/openapi.json`` from them, which can be imported directly into Insomnia,
Bruno, ApiDog, Swagger UI, Postman, &c.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from ArcheoConverter.core.models import ModelElement, ModelRelationship
from ArcheoConverter.services.comparator import ApplyReport, ComparisonResult, IntegrationPlan
from ArcheoConverter.services.converter import ConversionReport
from ArcheoConverter.services.exporter import ExportRequest, ExportReport
from ArcheoConverter.services.importer import ImportResult
from ArcheoConverter.services.search import GraphPayload, SearchPage
from ArcheoConverter.services.summarizer import ComparisonSummary, ModelSummary


# --------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------- #
def explode_csv(values: list[str]) -> list[str]:
    """Split comma-separated query parameters into individual values.

    Both ``?types=a,b`` and ``?types=a&types=b`` are supported by the
    endpoints (the latter arrives pre-split by FastAPI).
    """
    result: list[str] = []
    for value in values:
        result.extend(part.strip() for part in value.split(",") if part.strip())
    return result


# --------------------------------------------------------------------- #
# Meta
# --------------------------------------------------------------------- #
class FormalismDescriptor(BaseModel):
    """One registered formalism (API facing)."""

    formalism: str
    version: str
    description: str
    importable: bool = True
    exportable: bool = False
    default_version: bool = False


class ConversionDescriptor(BaseModel):
    """One available conversion (API facing)."""

    id: str
    source_formalism: str
    source_versions: list[str]
    target_formalism: str
    target_versions: list[str]
    description: str = ""


class MetaResponse(BaseModel):
    """Response of ``GET /meta``."""

    app: str
    version: str
    description: str
    formalisms: list[FormalismDescriptor]
    conversions: list[ConversionDescriptor]
    ui: bool
    openapi: str
    docs: str


# --------------------------------------------------------------------- #
# Models
# --------------------------------------------------------------------- #
class ModelListItem(BaseModel):
    """One entry of the model list."""

    model_id: str
    name: str
    formalism: str
    version: str
    source_file: str | None = None
    imported_at: str
    element_count: int
    relationship_count: int
    folder_count: int


class ModelDetail(BaseModel):
    """Full detail of one loaded model."""

    model_id: str
    name: str
    formalism: str
    version: str
    source_file: str | None = None
    imported_at: str
    notes: str = ""
    element_count: int = 0
    relationship_count: int = 0
    folder_count: int = 0
    summary: ModelSummary


class FolderTreeNode(BaseModel):
    """One node of the folder tree (recursive)."""

    id: str
    name: str
    kind: str
    description: str = ""
    parent_id: str | None = None
    element_count: int = 0
    children: list["FolderTreeNode"] = Field(default_factory=list)


class FolderDetail(BaseModel):
    """One folder and the entities it contains."""

    id: str
    name: str
    kind: str
    description: str = ""
    parent_id: str | None = None
    elements: list[ModelElement] = Field(default_factory=list)
    relationships: list[ModelRelationship] = Field(default_factory=list)


class ElementDetail(BaseModel):
    """One element plus its inbound/outbound relationships."""

    element: ModelElement
    inbound: list[ModelRelationship] = Field(default_factory=list)
    outbound: list[ModelRelationship] = Field(default_factory=list)


class RelationshipPage(BaseModel):
    """One page of relationships."""

    total: int
    offset: int
    limit: int
    items: list[ModelRelationship]


class ImportJsonRequest(BaseModel):
    """JSON based import request (alternative to the multipart upload)."""

    model_id: str | None = None
    name: str | None = None
    filename: str | None = None
    formalism: str | None = None
    version: str | None = None
    overwrite: bool = False
    content: str | None = Field(
        default=None,
        description="Raw XML content (use this OR content_base64).",
    )
    content_base64: str | None = Field(
        default=None,
        description="Base64 encoded XML content (use this OR content).",
    )


class PagedElementsResponse(BaseModel):
    """Alias kept for OpenAPI readability of the elements endpoint."""

    page: SearchPage


# --------------------------------------------------------------------- #
# Convert
# --------------------------------------------------------------------- #
class ConvertRequest(BaseModel):
    """Request body of ``POST /convert``."""

    model_id: str
    target_formalism: str = "archimate"
    target_version: str = "4.0"
    dry_run: bool = False
    name: str | None = None
    model_id_new: str | None = Field(default=None, description="Id of the new model")
    element_policy: str | None = Field(
        default=None, description="Override the rule policy: keep|stereotype|drop"
    )
    relationship_policy: str | None = Field(
        default=None, description="Override the rule policy: drop|keep"
    )


class ConvertResponse(BaseModel):
    """Response of ``POST /convert``."""

    report: ConversionReport
    model_id: str | None = None


# --------------------------------------------------------------------- #
# Compare
# --------------------------------------------------------------------- #
class CompareRequest(BaseModel):
    """Request body of ``POST /compare``."""

    base_id: str
    other_id: str
    match_by: str | None = Field(
        default=None, description="id | name | id_then_name (default from config)"
    )


class CompareResponse(BaseModel):
    """Response of ``POST /compare`` (report stored in-memory)."""

    report_id: str
    result: ComparisonResult
    summary: ComparisonSummary


class PlanRequest(BaseModel):
    """Request body of ``POST /compare/integration-plan``."""

    base_id: str
    source_id: str
    include_removals: bool = False
    match_by: str | None = None


class PlanResponse(BaseModel):
    """Response of ``POST /compare/integration-plan``."""

    report_id: str
    plan: IntegrationPlan


class ApplyResponse(BaseModel):
    """Response of ``POST /compare/apply``."""

    applied: ApplyReport
    model: ModelDetail


# --------------------------------------------------------------------- #
# Admin
# --------------------------------------------------------------------- #
class StatsResponse(BaseModel):
    """Response of ``GET /admin/stats``."""

    models: int
    elements: int
    relationships: int
    folders: int
    reports: int
    memory_estimate_bytes: int
    by_formalism: dict[str, int]
    uptime_seconds: float


class PurgeResponse(BaseModel):
    """Response of ``POST /admin/purge``."""

    deleted_models: int
    deleted_reports: int = 0


# --------------------------------------------------------------------- #
# Misc
# --------------------------------------------------------------------- #
class ExportJsonResponse(BaseModel):
    """``format=json`` variant of the export endpoint."""

    report: ExportReport
    xml: str
    markdown: str


class OkResponse(BaseModel):
    """Generic acknowledgement."""

    ok: bool = True
    message: str = ""
    extra: dict[str, Any] = Field(default_factory=dict)


FolderTreeNode.model_rebuild()
