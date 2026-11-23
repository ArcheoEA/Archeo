"""In-memory model repository.

The repository is the single place where loaded models live. It is:

* **in-memory by design** (no database dependency): models are plain
  Pydantic objects held in a dictionary;
* **thread-safe**: every public operation is guarded by a re-entrant lock so
  the ASGI server (multi-threaded event loop / workers) can serve
  concurrent requests safely;
* **unlimited in count**: any number of models can be loaded simultaneously,
  which is what enables the two-model comparison feature.

A companion :class:`ReportStore` keeps transient reports (comparisons,
integration plans) keyed by id so the UI and API clients can re-fetch them.
"""

from __future__ import annotations

import logging
import sys
import threading
from typing import Any

from ArcheoConverter.core.models import Model
from ArcheoConverter.exceptions import ModelAlreadyExistsError, ModelNotFoundError, ReportNotFoundError

logger = logging.getLogger("archeoconverter.repository")


def estimate_bytes(obj: Any, seen: set[int] | None = None) -> int:
    """Roughly estimate the memory footprint of a Python object tree.

    This is intentionally a cheap approximation (it does not traverse into
    Pydantic internals beyond ``__dict__``) that is good enough for the
    ``/admin/stats`` endpoint.
    """
    if seen is None:
        seen = set()
    obj_id = id(obj)
    if obj_id in seen:
        return 0
    seen.add(obj_id)

    size = sys.getsizeof(obj)
    if isinstance(obj, dict):
        for key, value in obj.items():
            size += estimate_bytes(key, seen) + estimate_bytes(value, seen)
    elif isinstance(obj, (list, tuple, set, frozenset)):
        for item in obj:
            size += estimate_bytes(item, seen)
    elif hasattr(obj, "__dict__"):
        for value in vars(obj).values():
            size += estimate_bytes(value, seen)
    return size


class ModelRepository:
    """Thread-safe in-memory store of :class:`Model` instances."""

    def __init__(self) -> None:
        self._models: dict[str, Model] = {}
        self._lock = threading.RLock()
        self.reports = ReportStore()

    # ------------------------------------------------------------------ #
    # CRUD
    # ------------------------------------------------------------------ #
    def add(self, model: Model, *, overwrite: bool = False) -> Model:
        """Store a model.

        Args:
            model: the model to store (its ``metadata.model_id`` is the key).
            overwrite: when True, replace an existing model with the same id.

        Raises:
            ModelAlreadyExistsError: if the id exists and ``overwrite`` is False.
        """
        with self._lock:
            if model.model_id in self._models and not overwrite:
                raise ModelAlreadyExistsError(
                    f"Model '{model.model_id}' is already loaded.",
                    details=["pass overwrite=true to replace it"],
                )
            self._models[model.model_id] = model
        logger.info(
            "model stored: id=%s name=%r formalism=%s version=%s elements=%d relationships=%d folders=%d",
            model.model_id,
            model.metadata.name,
            model.metadata.formalism,
            model.metadata.version,
            len(model.elements),
            len(model.relationships),
            len(model.folders),
        )
        return model

    def replace(self, model: Model) -> Model:
        """Store a model, replacing any existing model with the same id."""
        return self.add(model, overwrite=True)

    def get(self, model_id: str) -> Model:
        """Return a model by id.

        Raises:
            ModelNotFoundError: when no model with that id is loaded.
        """
        with self._lock:
            model = self._models.get(model_id)
        if model is None:
            raise ModelNotFoundError(f"Model '{model_id}' is not loaded.")
        return model

    def list(self) -> list[Model]:
        """Return all loaded models, sorted by import date (oldest first)."""
        with self._lock:
            models = list(self._models.values())
        models.sort(key=lambda m: (m.metadata.imported_at, m.model_id))
        return models

    def remove(self, model_id: str) -> bool:
        """Remove a model. Return True when a model was actually removed."""
        with self._lock:
            removed = self._models.pop(model_id, None) is not None
        if removed:
            logger.info("model removed: id=%s", model_id)
        return removed

    def clear(self) -> int:
        """Remove every model and report. Return the number of models removed."""
        with self._lock:
            count = len(self._models)
            self._models.clear()
            self.reports.clear()
        logger.info("repository cleared: %d model(s) removed", count)
        return count

    # ------------------------------------------------------------------ #
    # Introspection
    # ------------------------------------------------------------------ #
    def __len__(self) -> int:
        with self._lock:
            return len(self._models)

    def contains(self, model_id: str) -> bool:
        """Return True when a model with that id is loaded."""
        with self._lock:
            return model_id in self._models

    def stats(self) -> dict[str, Any]:
        """Return aggregate statistics over all loaded models."""
        with self._lock:
            models = list(self._models.values())
        return {
            "models": len(models),
            "elements": sum(len(m.elements) for m in models),
            "relationships": sum(len(m.relationships) for m in models),
            "folders": sum(len(m.folders) for m in models),
            "reports": self.reports.count(),
            "memory_estimate_bytes": sum(estimate_bytes(m) for m in models),
            "by_formalism": self._by_formalism(models),
        }

    @staticmethod
    def _by_formalism(models: list[Model]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for model in models:
            key = f"{model.metadata.formalism}:{model.metadata.version or '?'}"
            counts[key] = counts.get(key, 0) + 1
        return counts


class ReportStore:
    """Small in-memory store for transient reports (comparisons, plans)."""

    def __init__(self) -> None:
        self._items: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()

    def store(self, report_id: str, kind: str, payload: dict[str, Any]) -> None:
        """Store (or overwrite) a report under ``report_id``."""
        with self._lock:
            self._items[report_id] = {"report_id": report_id, "kind": kind, "payload": payload}

    def get(self, report_id: str) -> dict[str, Any]:
        """Return a stored report.

        Raises:
            ReportNotFoundError: when the report id is unknown.
        """
        with self._lock:
            item = self._items.get(report_id)
        if item is None:
            raise ReportNotFoundError(f"Report '{report_id}' was not found (reports are in-memory).")
        return item

    def list(self, kind: str | None = None) -> list[dict[str, Any]]:
        """Return stored report headers, optionally filtered by ``kind``."""
        with self._lock:
            items = [
                {"report_id": item["report_id"], "kind": item["kind"]}
                for item in self._items.values()
                if kind is None or item["kind"] == kind
            ]
        return items

    def count(self) -> int:
        """Return the number of stored reports."""
        with self._lock:
            return len(self._items)

    def clear(self, kind: str | None = None) -> int:
        """Remove stored reports (optionally only of a given ``kind``)."""
        with self._lock:
            if kind is None:
                removed = len(self._items)
                self._items.clear()
            else:
                removed = sum(1 for item in self._items.values() if item["kind"] == kind)
                self._items = {
                    rid: item for rid, item in self._items.items() if item["kind"] != kind
                }
        return removed
