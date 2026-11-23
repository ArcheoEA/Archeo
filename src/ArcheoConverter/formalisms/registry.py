"""Formalism registry: the extension point for supported modeling languages.

The registry maps ``(formalism, version)`` to a
:class:`~ArcheoConverter.formalisms.base.FormalismHandler` and drives
automatic content detection. The *default registry* ships with the four
built-in formalisms:

* ``archimate`` 3.2 and 4.0 (primary formalism, import + export);
* ``bpmn`` 2.0, ``uml`` 2.5, ``sysml`` 1.4 (dedicated import extensions,
  convertible to ArchiMate).

New formalisms can be registered at runtime (``register``) which is how the
application is extended with "dedicated parameters" as required.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from ArcheoConverter.exceptions import UnsupportedFormalismError, UnsupportedVersionError
from ArcheoConverter.formalisms.archimate.parser import ArchiMateHandler
from ArcheoConverter.formalisms.base import FormalismHandler
from ArcheoConverter.formalisms.bpmn.parser import BpmnHandler
from ArcheoConverter.formalisms.sysml.parser import SysmlHandler
from ArcheoConverter.formalisms.uml.parser import UmlHandler

logger = logging.getLogger("archeoconverter.formalisms")


@dataclass(frozen=True)
class FormalismInfo:
    """Public description of a registered formalism (API/UI facing)."""

    formalism: str
    version: str
    description: str
    importable: bool = True
    exportable: bool = False
    default_version: bool = False


@dataclass
class _Entry:
    handler: FormalismHandler
    info: FormalismInfo = field(default_factory=lambda: FormalismInfo("", "", ""))


class FormalismRegistry:
    """Registry of formalism handlers keyed by ``(formalism, version)``."""

    def __init__(self) -> None:
        self._entries: dict[tuple[str, str], _Entry] = {}

    # ------------------------------------------------------------------ #
    # Registration
    # ------------------------------------------------------------------ #
    def register(
        self,
        handler: FormalismHandler,
        *,
        version: str,
        description: str = "",
        importable: bool = True,
        exportable: bool = False,
        default_version: bool = False,
    ) -> None:
        """Register a handler for ``handler.formalism`` at ``version``.

        Re-registering the same ``(formalism, version)`` replaces the
        previous handler, which is how configuration can override built-ins.
        """
        key = (handler.formalism, version)
        info = FormalismInfo(
            formalism=handler.formalism,
            version=version,
            description=description or handler.description,
            importable=importable,
            exportable=exportable,
            default_version=default_version,
        )
        self._entries[key] = _Entry(handler=handler, info=info)
        logger.info("formalism registered: %s:%s", handler.formalism, version)

    # ------------------------------------------------------------------ #
    # Lookup
    # ------------------------------------------------------------------ #
    def handler(self, formalism: str, version: str) -> FormalismHandler:
        """Return the handler for ``formalism:version``.

        Raises:
            UnsupportedFormalismError: when the formalism is unknown.
            UnsupportedVersionError: when the version is not registered.
        """
        entry = self._entries.get((formalism, version))
        if entry is None:
            known = sorted(v for (f, v) in self._entries if f == formalism)
            if known:
                raise UnsupportedVersionError(
                    f"Unsupported version '{version}' for formalism '{formalism}'.",
                    details=[f"supported versions: {', '.join(known)}"],
                )
            all_formalisms = sorted({f for (f, _) in self._entries})
            raise UnsupportedFormalismError(
                f"Unsupported formalism '{formalism}'.",
                details=[f"supported formalisms: {', '.join(all_formalisms)}"],
            )
        return entry.handler

    def versions(self, formalism: str) -> list[str]:
        """Return the registered versions of a formalism (possibly empty)."""
        return sorted(v for (f, v) in self._entries if f == formalism)

    def formalisms(self) -> list[str]:
        """Return every registered formalism id, sorted."""
        return sorted({f for (f, _) in self._entries})

    def infos(self) -> list[FormalismInfo]:
        """Return public descriptions of every registered formalism."""
        return [entry.info for (_, entry) in sorted(self._entries.items())]

    def default_version(self, formalism: str) -> str | None:
        """Return the default version of a formalism (or its first version)."""
        versions = self.versions(formalism)
        if not versions:
            return None
        for (f, v), entry in self._entries.items():
            if f == formalism and entry.info.default_version:
                return v
        return versions[0]

    # ------------------------------------------------------------------ #
    # Detection
    # ------------------------------------------------------------------ #
    def detect(self, content: bytes, filename: str | None) -> tuple[str, str]:
        """Auto-detect the ``(formalism, version)`` of a payload.

        Every registered handler gets a chance to claim the content; the
        first positive answer wins. ArchiMate is tried last because its
        generic ``<model>`` root is the least specific.

        Raises:
            UnsupportedFormalismError: when no handler recognizes the payload.
        """
        for (formalism, _version), entry in self._entries.items():
            if formalism == "archimate":
                continue
            detected = entry.handler.detect(content, filename)
            if detected is not None:
                return formalism, detected
        # ArchiMate fallback.
        for (formalism, _version), entry in self._entries.items():
            if formalism != "archimate":
                continue
            detected = entry.handler.detect(content, filename)
            if detected is not None:
                return formalism, detected
        raise UnsupportedFormalismError(
            "Unable to detect the formalism of the submitted content.",
            details=[
                "supported formalisms: " + ", ".join(self.formalisms()),
                "you can force one with the 'formalism' and 'version' parameters",
            ],
        )


def default_registry() -> FormalismRegistry:
    """Build the registry with all built-in formalism handlers.

    This is the single place where the *dedicated parameters* that extend
    the set of supported original formalisms (BPMN, UML, SysML) are wired
    in: each handler is an independent, swappable module.
    """
    registry = FormalismRegistry()
    archimate = ArchiMateHandler()
    registry.register(
        archimate, version="3.2", description="ArchiMate 3.2 (Open Group)",
        importable=True, exportable=True, default_version=True,
    )
    registry.register(
        archimate, version="4.0", description="ArchiMate 4.0 (Open Group)",
        importable=True, exportable=True,
    )
    registry.register(
        BpmnHandler(), version="2.0", description="BPMN 2.0 (OMG)",
        importable=True, exportable=False, default_version=True,
    )
    registry.register(
        UmlHandler(), version="2.5", description="UML 2.5 via XMI 2.x (OMG)",
        importable=True, exportable=False, default_version=True,
    )
    registry.register(
        SysmlHandler(), version="1.4", description="SysML 1.4 via XMI (OMG/Eclipse)",
        importable=True, exportable=False, default_version=True,
    )
    return registry
