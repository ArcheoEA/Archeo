"""Tests for :mod:`AcheoConverter.exceptions` (error hierarchy + payloads)."""

from __future__ import annotations

from AcheoConverter.exceptions import (
    AcheoConverterError,
    ComparisonError,
    ConversionError,
    ExportError,
    GraphTooLargeError,
    ModelAlreadyExistsError,
    ModelImportError,
    ModelNotFoundError,
    PayloadTooLargeError,
    ReportNotFoundError,
    UnsupportedFormalismError,
    UnsupportedVersionError,
)


def test_base_error_attributes():
    """Every error carries a code, an http status and a detail list."""
    error = AcheoConverterError("boom", details=["a", "b"])
    assert error.code == "internal_error"
    assert error.http_status == 500
    assert error.details == ["a", "b"]
    assert str(error) == "boom"


def test_to_payload_shape():
    """The API payload is {detail, code, details}."""
    error = ModelNotFoundError("nope")
    payload = error.to_payload()
    assert payload == {"detail": "nope", "code": "model_not_found", "details": []}


def test_status_mapping():
    """Each domain error maps to a sensible HTTP status."""
    cases = [
        (ModelNotFoundError("x"), 404),
        (ModelAlreadyExistsError("x"), 409),
        (ModelImportError("x"), 422),
        (UnsupportedFormalismError("x"), 415),
        (UnsupportedVersionError("x"), 422),
        (ConversionError("x"), 422),
        (ComparisonError("x"), 409),
        (ExportError("x"), 422),
        (PayloadTooLargeError("x"), 413),
        (GraphTooLargeError("x"), 413),
        (ReportNotFoundError("x"), 404),
    ]
    for error, expected in cases:
        assert error.http_status == expected, type(error).__name__
        assert error.code != "internal_error"


def test_all_domain_errors_derive_from_base():
    """The whole hierarchy derives from AcheoConverterError (one handler)."""
    classes = [
        ModelNotFoundError, ModelAlreadyExistsError, ModelImportError,
        UnsupportedFormalismError, UnsupportedVersionError, ConversionError,
        ComparisonError, ExportError, PayloadTooLargeError, GraphTooLargeError,
        ReportNotFoundError,
    ]
    for cls in classes:
        assert issubclass(cls, AcheoConverterError)
