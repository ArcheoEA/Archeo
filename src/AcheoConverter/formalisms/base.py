"""Base abstractions shared by every formalism handler.

A *formalism handler* knows how to:

1. **detect** whether a byte payload belongs to its formalism;
2. **parse** that payload into the canonical in-memory :class:`Model`.

Handlers are registered in a :class:`~AcheoConverter.formalisms.registry.FormalismRegistry`
which is what makes the set of supported formalisms extensible: new
formalisms (or new versions of an existing one) can be plugged in through
configuration without touching the engine core.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from AcheoConverter.exceptions import ModelImportError

# --------------------------------------------------------------------- #
# Name conversion helpers (camelCase <-> kebab-case)
# --------------------------------------------------------------------- #
_CAMEL_TO_KEBAB_1 = re.compile(r"([A-Z]+)([A-Z][a-z])")
_CAMEL_TO_KEBAB_2 = re.compile(r"([a-z0-9])([A-Z])")


def to_kebab(name: str) -> str:
    """Convert ``camelCase``/``PascalCase`` to ``kebab-case``.

    Examples: ``businessActor`` -> ``business-actor``,
    ``HTMLParser`` -> ``html-parser``.
    """
    value = _CAMEL_TO_KEBAB_1.sub(r"\1-\2", name)
    value = _CAMEL_TO_KEBAB_2.sub(r"\1-\2", value)
    return value.lower()


def to_camel(name: str) -> str:
    """Convert ``kebab-case`` to ``camelCase`` (first letter lowercased)."""
    parts = [part for part in name.split("-") if part]
    if not parts:
        return name
    return parts[0].lower() + "".join(part[:1].upper() + part[1:] for part in parts[1:])


def xml_local_name(tag: Any) -> str:
    """Return the local (namespace-free) name of an ElementTree tag.

    Non-string tags (comments, processing instructions) yield ``""``.
    """
    if not isinstance(tag, str):
        return ""
    return tag.rsplit("}", 1)[-1]


def xml_namespace(tag: Any) -> str:
    """Return the namespace URI of an ElementTree tag ('' when absent)."""
    if not isinstance(tag, str) or not tag.startswith("{"):
        return ""
    return tag[1 : tag.index("}")]


def attr_id(elem: Any) -> str | None:
    """Return the identifier of an XML element.

    The plain ``id`` attribute wins; otherwise the first ``xmi:id`` style
    (namespace-qualified) ``id`` attribute is used. Returns ``None`` when
    the element has no identifier at all.
    """
    for key, value in elem.attrib.items():
        if xml_local_name(key) == "id" and value:
            return value
    return None


# --------------------------------------------------------------------- #
# Parsed model
# --------------------------------------------------------------------- #
@dataclass
class ParsedModel:
    """Intermediate result produced by a formalism parser.

    Parsers fill this structure (elements / relationships / folders as plain
    dicts) and the *import service* turns it into a fully validated
    :class:`~AcheoConverter.core.models.Model`, guaranteeing unique ids and
    referential integrity.
    """

    formalism: str = ""
    version: str = ""
    name: str = ""
    elements: list[dict[str, Any]] = field(default_factory=list)
    relationships: list[dict[str, Any]] = field(default_factory=list)
    folders: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    extras: dict[str, Any] = field(default_factory=dict)

    def to_model(self, *, model_id: str | None = None, name: str | None = None) -> "Any":
        """Build the canonical in-memory ``Model`` from parsed data.

        Args:
            model_id: explicit model id (a random one is generated when None).
            name: explicit model name (the parser-provided name or a generic
                fallback is used when None).
        """
        # Imported here to avoid a circular import at module load time.
        from AcheoConverter.core.models import (
            Model,
            ModelElement,
            ModelFolder,
            ModelMetadata,
            ModelRelationship,
            new_id,
            utcnow,
        )

        metadata = ModelMetadata(
            model_id=model_id or new_id("model"),
            name=name or self.name or f"{self.formalism} model",
            formalism=self.formalism,
            version=self.version,
            notes=f"Imported by the {self.formalism} formalism handler",
            imported_at=utcnow(),
        )
        return Model(
            metadata=metadata,
            elements={e["id"]: ModelElement.model_validate(e) for e in self.elements},
            relationships={
                r["id"]: ModelRelationship.model_validate(r) for r in self.relationships
            },
            folders={f["id"]: ModelFolder.model_validate(f) for f in self.folders},
        )


# --------------------------------------------------------------------- #
# Handler abstraction
# --------------------------------------------------------------------- #
class FormalismHandler(ABC):
    """Interface every formalism parser must implement."""

    #: formalism identifier, e.g. ``"archimate"``.
    formalism: str = "unknown"
    #: formalism versions this handler can parse, e.g. ``("3.2", "4.0")``.
    supported_versions: tuple[str, ...] = ()
    #: human readable description (shown by the API / UI).
    description: str = ""

    @abstractmethod
    def detect(self, content: bytes, filename: str | None) -> str | None:
        """Return the detected formalism version, or ``None`` when the payload
        does not look like this formalism.

        Detection must be cheap (it runs before a full parse) and tolerant:
        a slight uncertainty is acceptable because the import service can
        force a formalism / version explicitly.
        """

    @abstractmethod
    def parse(
        self,
        content: bytes,
        filename: str | None,
        *,
        version: str | None = None,
        name: str | None = None,
        model_id: str | None = None,
    ) -> ParsedModel:
        """Parse ``content`` into a :class:`ParsedModel`.

        Args:
            content: raw file bytes (XML).
            filename: original file name (used for hints / metadata).
            version: formalism version to parse as (auto-detected when None).
            name: model name override.
            model_id: model id override.

        Raises:
            ModelImportError: when the payload cannot be parsed.
        """

    # ------------------------------------------------------------------ #
    # Shared helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def parse_xml(content: bytes, *, context: str) -> Any:
        """Parse bytes as XML, raising a domain error on failure.

        Args:
            content: raw bytes to parse.
            context: human readable context (file name) for error messages.
        """
        import xml.etree.ElementTree as ET

        try:
            return ET.fromstring(content)
        except ET.ParseError as exc:
            raise ModelImportError(f"Invalid XML in {context}: {exc}", details=[context]) from exc
        except ValueError as exc:  # e.g. null byte in input
            raise ModelImportError(f"Invalid XML in {context}: {exc}", details=[context]) from exc
