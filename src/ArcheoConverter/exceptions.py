"""Exception hierarchy for ArcheoConverter.

Every error raised inside the engine derives from :class:`ArcheoConverterError`,
which carries a machine readable ``code`` and an HTTP status so that the API
layer can translate domain errors into consistent HTTP responses.
"""

from __future__ import annotations

from typing import Any


class ArcheoConverterError(Exception):
    """Base class for all ArcheoConverter errors.

    Attributes:
        code: stable machine readable error code (used in API error payloads).
        http_status: HTTP status code associated with this error class.
        details: optional list of human readable detail lines.
    """

    code: str = "internal_error"
    http_status: int = 500

    def __init__(self, message: str, *, details: list[str] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details: list[str] = list(details) if details else []

    def to_payload(self) -> dict[str, Any]:
        """Build the JSON error payload returned by the API."""
        return {
            "detail": self.message,
            "code": self.code,
            "details": self.details,
        }


class ConfigError(ArcheoConverterError):
    """The application configuration is missing or invalid."""

    code = "config_error"
    http_status = 500


class ModelNotFoundError(ArcheoConverterError):
    """The requested model id does not exist in the in-memory repository."""

    code = "model_not_found"
    http_status = 404


class ModelAlreadyExistsError(ArcheoConverterError):
    """A model with the same id is already loaded and ``overwrite`` was false."""

    code = "model_already_exists"
    http_status = 409


class ModelImportError(ArcheoConverterError):
    """The submitted content could not be parsed as a model file."""

    code = "model_import_error"
    http_status = 422


class UnsupportedFormalismError(ArcheoConverterError):
    """No formalism handler matches the content / the requested formalism."""

    code = "unsupported_formalism"
    http_status = 415


class UnsupportedVersionError(ArcheoConverterError):
    """The requested formalism version is not supported."""

    code = "unsupported_version"
    http_status = 422


class ConversionError(ArcheoConverterError):
    """A model conversion is not possible (unsupported path, bad options...)."""

    code = "conversion_error"
    http_status = 422


class ComparisonError(ArcheoConverterError):
    """The two models cannot be compared (different formalisms, missing ids...)."""

    code = "comparison_error"
    http_status = 409


class ExportError(ArcheoConverterError):
    """A model export is not possible (bad selection, unsupported target...)."""

    code = "export_error"
    http_status = 422


class PayloadTooLargeError(ArcheoConverterError):
    """The uploaded payload exceeds the configured maximum size."""

    code = "payload_too_large"
    http_status = 413


class GraphTooLargeError(ArcheoConverterError):
    """The requested graph exceeds the configured node limit."""

    code = "graph_too_large"
    http_status = 413


class ReportNotFoundError(ArcheoConverterError):
    """A stored report (comparison / plan) id does not exist."""

    code = "report_not_found"
    http_status = 404
