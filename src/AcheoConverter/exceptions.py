"""Exception hierarchy for AcheoConverter.

Every error raised inside the engine derives from :class:`AcheoConverterError`,
which carries a machine readable ``code`` and an HTTP status so that the API
layer can translate domain errors into consistent HTTP responses.
"""

from __future__ import annotations

from typing import Any


class AcheoConverterError(Exception):
    """Base class for all AcheoConverter errors.

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


class ConfigError(AcheoConverterError):
    """The application configuration is missing or invalid."""

    code = "config_error"
    http_status = 500


class ModelNotFoundError(AcheoConverterError):
    """The requested model id does not exist in the in-memory repository."""

    code = "model_not_found"
    http_status = 404


class ModelAlreadyExistsError(AcheoConverterError):
    """A model with the same id is already loaded and ``overwrite`` was false."""

    code = "model_already_exists"
    http_status = 409


class ModelImportError(AcheoConverterError):
    """The submitted content could not be parsed as a model file."""

    code = "model_import_error"
    http_status = 422


class UnsupportedFormalismError(AcheoConverterError):
    """No formalism handler matches the content / the requested formalism."""

    code = "unsupported_formalism"
    http_status = 415


class UnsupportedVersionError(AcheoConverterError):
    """The requested formalism version is not supported."""

    code = "unsupported_version"
    http_status = 422


class ConversionError(AcheoConverterError):
    """A model conversion is not possible (unsupported path, bad options...)."""

    code = "conversion_error"
    http_status = 422


class ComparisonError(AcheoConverterError):
    """The two models cannot be compared (different formalisms, missing ids...)."""

    code = "comparison_error"
    http_status = 409


class ExportError(AcheoConverterError):
    """A model export is not possible (bad selection, unsupported target...)."""

    code = "export_error"
    http_status = 422


class PayloadTooLargeError(AcheoConverterError):
    """The uploaded payload exceeds the configured maximum size."""

    code = "payload_too_large"
    http_status = 413


class GraphTooLargeError(AcheoConverterError):
    """The requested graph exceeds the configured node limit."""

    code = "graph_too_large"
    http_status = 413


class ReportNotFoundError(AcheoConverterError):
    """A stored report (comparison / plan) id does not exist."""

    code = "report_not_found"
    http_status = 404
