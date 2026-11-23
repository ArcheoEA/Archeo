"""Shared XMI 2.x walker used by the UML and SysML handlers.

Both UML and SysML are exchanged as XMI: an ``<xmi:XMI>`` root containing
model elements in a formalism-specific namespace. This module performs the
formalism-agnostic part of the work:

* walk the whole document tree (namespace tolerant);
* collect every model element as an :class:`XmiNode` (id, type, name,
  explicit references, parent link, document order, raw attributes);
* resolve *single-valued* references: any attribute whose value matches a
  known element id (e.g. ``client``, ``supplier``, ``source``, ``type``).

Attribute semantics follow XMI 2.x:

* ``xmi:type`` (namespace-qualified) holds the element's type name
  (e.g. ``uml:Class``);
* a local ``type`` attribute is a **reference to a classifier**
  (e.g. the type of a UML property);
* ``xmi:references`` carries multi-valued references (space separated ids).

The formalism mappers (UML / SysML) then turn this flat node list into the
canonical in-memory model.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from ArcheoConverter.exceptions import ModelImportError
from ArcheoConverter.formalisms.base import attr_id, xml_local_name

logger = logging.getLogger("archeoconverter.xmi")

#: Attribute local names that never represent references to model elements.
#: (``type`` is deliberately NOT listed: in XMI 2.x a local ``type``
#: attribute is a classifier reference, while the type *name* lives in the
#: namespace-qualified ``xmi:type`` attribute.)
_NON_REF_ATTRIBUTES = {
    "id", "name", "visibility", "ordered", "unique", "changeability",
    "isAbstract", "isFinal", "isComposite", "isLeaf", "isService", "isDerived",
    "isReadOnly", "isUnordered", "isUnion", "isReentrant", "isSynchronous",
    "isUninterruptible", "isMultiplied", "isPrimary", "isSecondary",
    "lowerValue", "upperValue",
}


@dataclass
class XmiNode:
    """One model element found in an XMI document."""

    node_id: str
    type_name: str  # local type name, e.g. "Class", "BlockDefinition"
    name: str = ""
    namespace: str = ""
    parent_id: str | None = None
    refs: list[str] = field(default_factory=list)  # multi-valued references
    single_refs: dict[str, str] = field(default_factory=dict)  # attr -> target id
    attrs: dict[str, str] = field(default_factory=dict)  # raw attributes
    order: int = 0  # document order (stable sorting)


def parse_xmi(content: bytes, *, context: str) -> tuple[list[XmiNode], list[str]]:
    """Parse XMI content into a flat list of :class:`XmiNode`.

    Args:
        content: raw XMI bytes.
        context: human readable context (file name) for error messages.

    Returns:
        A tuple ``(nodes, warnings)``. ``nodes`` is in document order.

    Raises:
        ModelImportError: when the payload is not well-formed XML or does
            not look like XMI (no ``<xmi:XMI>`` root).
    """
    import xml.etree.ElementTree as ET

    try:
        root = ET.fromstring(content)
    except ET.ParseError as exc:
        raise ModelImportError(f"Invalid XML in {context}: {exc}", details=[context]) from exc

    if xml_local_name(root.tag) != "XMI":
        raise ModelImportError(
            f"Expected an XMI document (root '<xmi:XMI>') in {context}.",
            details=[f"found root: {xml_local_name(root.tag) or '?'}"],
        )

    nodes: list[XmiNode] = []
    warnings: list[str] = []
    order = 0

    def walk(elem: Any, parent_id: str | None) -> None:
        nonlocal order
        for child in elem:
            if not isinstance(child.tag, str):
                continue  # skip comments / processing instructions
            child_id = attr_id(child)
            if child_id is None:
                # Structural XMI nodes (e.g. <xmi:Extension>) carry no id:
                # descend without registering them.
                walk(child, parent_id)
                continue
            node = XmiNode(
                node_id=child_id,
                type_name=_node_type(child),
                name=(child.get("name") or "").strip(),
                namespace=_namespace(child.tag),
                parent_id=parent_id,
                attrs=dict(child.attrib),
                order=order,
            )
            order += 1
            for key, value in child.attrib.items():
                if xml_local_name(key) == "references" and value:
                    node.refs.extend(ref for ref in value.split() if ref)
            nodes.append(node)
            walk(child, child_id)

    walk(root, None)

    # Second pass: resolve single-valued references (attribute value is a
    # known element id), e.g. client/supplier, source/target, type=... .
    known_ids = {node.node_id for node in nodes}
    for node in nodes:
        for key, value in node.attrs.items():
            local = xml_local_name(key)
            if local in _NON_REF_ATTRIBUTES:
                continue
            if value in known_ids and value != node.node_id:
                node.single_refs.setdefault(local, value)

    if not nodes:
        warnings.append("The XMI document contains no model elements.")
    return nodes, warnings


def _node_type(elem: Any) -> str:
    """Determine the local type name of an XMI element.

    The namespace-qualified ``xmi:type`` attribute wins (it may carry a
    qualified name such as ``uml:Class``); otherwise the tag's local name
    is used. A local ``type`` attribute is a classifier reference and is
    never treated as a type name.
    """
    for key, value in elem.attrib.items():
        if key.startswith("{") and xml_local_name(key) == "type" and value:
            return value.split(":")[-1] if ":" in value else value
    return xml_local_name(elem.tag)


def _namespace(tag: Any) -> str:
    if not isinstance(tag, str) or not tag.startswith("{"):
        return ""
    return tag[1 : tag.index("}")]


def case_insensitive_lookup(types: dict[str, Any], name: str) -> str | None:
    """Return the key of ``types`` matching ``name`` case-insensitively.

    XMI producers are inconsistent about tag/attribute casing (``action`` vs
    ``Action``); parsers use this to normalize type names against their
    known type tables.
    """
    if name in types:
        return name
    lowered = name.lower()
    for key in types:
        if key.lower() == lowered:
            return key
    return None


def package_ancestor(node: XmiNode, nodes_by_id: dict[str, XmiNode],
                     package_types: frozenset[str]) -> str | None:
    """Return the id of the nearest package-like ancestor of ``node``.

    Walks the parent chain until a node whose type is in ``package_types``
    (e.g. ``Package`` / ``Model``) is found.
    """
    current = nodes_by_id.get(node.parent_id or "")
    while current is not None:
        if current.type_name in package_types:
            return current.node_id
        current = nodes_by_id.get(current.parent_id or "")
    return None
