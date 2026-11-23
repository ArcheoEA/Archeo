"""Search, navigation and graph extraction service.

Provides the read-side capabilities over any loaded model:

* **search** elements by free-text query (name / type / stereotype / tag),
  exact type list, stereotypes, tags, folder, extended properties - with
  relevance scoring and pagination;
* **navigate** the relationship graph from an element with a bounded
  depth and direction (out / in / both);
* **extract graphs** (nodes + edges) for a root element, a folder, or the
  whole model - the payload consumed by the visualization UI.

All operations are read-only and allocation-conscious; a configurable node
limit protects the server against exploding graphs on very large models.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

from ArcheoConverter.core.models import Model, ModelElement
from ArcheoConverter.exceptions import GraphTooLargeError, ModelNotFoundError

logger = logging.getLogger("archeoconverter.search")


class SearchPage(BaseModel):
    """One page of search results."""

    total: int
    offset: int
    limit: int
    items: list[ModelElement]


class GraphNode(BaseModel):
    """One node of a graph payload."""

    id: str
    name: str
    type: str
    stereotypes: list[str] = Field(default_factory=list)
    folder_id: str | None = None


class GraphEdge(BaseModel):
    """One edge of a graph payload."""

    id: str
    source: str
    target: str
    type: str
    aggregation: bool = False


class GraphPayload(BaseModel):
    """Graph payload for visualization (JSON friendly)."""

    model_id: str
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    truncated: bool = False
    root: str | None = None


class SearchService:
    """Search & navigation over in-memory models."""

    def __init__(self, *, max_results: int = 500, max_depth: int = 5, max_nodes: int = 2000) -> None:
        self._max_results = max_results
        self._max_depth = max_depth
        self._max_nodes = max_nodes

    # ------------------------------------------------------------------ #
    # Search
    # ------------------------------------------------------------------ #
    def search(
        self,
        model: Model,
        *,
        query: str | None = None,
        types: list[str] | None = None,
        stereotypes: list[str] | None = None,
        tags: list[str] | None = None,
        folder_id: str | None = None,
        property_key: str | None = None,
        property_value: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> SearchPage:
        """Search elements of a model.

        Filters are combined with AND. ``query`` is a free-text term matched
        (case-insensitively) against name, type, stereotypes and tags, with
        results ranked by relevance.
        """
        limit = max(1, min(limit, self._max_results))
        offset = max(0, offset)
        types_set = {t.lower() for t in types} if types else None
        stereo_set = set(stereotypes) if stereotypes else None
        tag_set = set(tags) if tags else None

        scored: list[tuple[int, str, ModelElement]] = []
        for element in model.elements.values():
            if folder_id is not None and element.folder_id != folder_id:
                continue
            if types_set is not None and element.type.lower() not in types_set:
                continue
            if stereo_set is not None and not (stereo_set & set(element.stereotypes)):
                continue
            element_tags = element.properties.get("__tags") or []
            if tag_set is not None and not (tag_set & set(element_tags)):
                continue
            if property_key is not None and property_key not in element.properties:
                continue
            if property_value is not None:
                value = element.properties.get(property_key)
                if str(value).lower() != property_value.lower():
                    continue

            if query is None:
                score = 0
            else:
                score = self._score(element, query.lower())
                if score <= 0:
                    continue

            scored.append((score, element.name.lower() or element.id, element))

        scored.sort(key=lambda item: (-item[0], item[1], item[2].id))
        total = len(scored)
        page = scored[offset : offset + limit]
        return SearchPage(total=total, offset=offset, limit=limit,
                          items=[element for _, _, element in page])

    @staticmethod
    def _score(element: ModelElement, query: str) -> int:
        """Relevance score of an element for a lower-cased query term."""
        score = 0
        name = element.name.lower()
        if name.startswith(query):
            score += 4
        elif query in name:
            score += 2
        if element.type.lower() == query:
            score += 3
        elif query in element.type.lower():
            score += 1
        if any(query in stereotype.lower() for stereotype in element.stereotypes):
            score += 2
        element_tags = element.properties.get("__tags") or []
        if any(query in tag.lower() for tag in element_tags):
            score += 2
        return score

    # ------------------------------------------------------------------ #
    # Navigation
    # ------------------------------------------------------------------ #
    def neighbors(
        self,
        model: Model,
        element_id: str,
        *,
        direction: str = "both",
        relationship_types: list[str] | None = None,
        depth: int = 1,
    ) -> GraphPayload:
        """Extract the neighborhood graph around an element (BFS).

        Args:
            model: the model to navigate.
            element_id: the root element id.
            direction: ``out`` (follow source->target), ``in`` (reverse),
                or ``both``.
            relationship_types: optional filter on relationship types.
            depth: maximum BFS depth (capped by the configured maximum).

        Raises:
            ModelNotFoundError: when the root element does not exist.
            GraphTooLargeError: when the neighborhood exceeds the node limit.
        """
        if element_id not in model.elements:
            raise ModelNotFoundError(f"Element '{element_id}' was not found in the model.")
        if direction not in ("out", "in", "both"):
            direction = "both"
        depth = max(1, min(depth, self._max_depth))
        rel_filter = {t.lower() for t in relationship_types} if relationship_types else None

        adjacency = self._adjacency(model, rel_filter)

        visited: set[str] = {element_id}
        frontier: list[str] = [element_id]
        edges: dict[str, Any] = {}
        for _ in range(depth):
            next_frontier: list[str] = []
            for node_id in frontier:
                for rel, other in adjacency.get(node_id, []):
                    if other in visited:
                        # Still record the edge (it bounds the subgraph).
                        edges[rel.id] = rel
                        continue
                    if len(visited) >= self._max_nodes:
                        return self._payload(model, visited, edges, root=element_id,
                                             truncated=True)
                    visited.add(other)
                    next_frontier.append(other)
                    edges[rel.id] = rel
            if not next_frontier:
                break
            frontier = next_frontier
        return self._payload(model, visited, edges, root=element_id, truncated=False)

    def folder_graph(self, model: Model, folder_id: str) -> GraphPayload:
        """Extract the full graph of a folder (and its sub-folders).

        Raises:
            ModelNotFoundError: when the folder does not exist.
            GraphTooLargeError: when the folder graph exceeds the node limit.
        """
        if folder_id not in model.folders:
            raise ModelNotFoundError(f"Folder '{folder_id}' was not found in the model.")
        node_ids = self._folder_element_ids(model, folder_id)
        if len(node_ids) > self._max_nodes:
            raise GraphTooLargeError(
                f"Folder '{folder_id}' contains {len(node_ids)} elements; the graph "
                f"limit is {self._max_nodes}. Use a narrower selection.",
            )
        edges = {}
        for rel in model.relationships.values():
            if rel.source in node_ids and rel.target in node_ids:
                edges[rel.id] = rel
        return self._payload(model, node_ids, edges, root=None, truncated=False)

    def model_graph(
        self,
        model: Model,
        *,
        element_types: list[str] | None = None,
    ) -> GraphPayload:
        """Extract the whole-model graph (optionally filtered by element type).

        Raises:
            GraphTooLargeError: when the model exceeds the node limit - the
                caller is then expected to narrow the request (folder / root).
        """
        if element_types:
            types_set = {t.lower() for t in element_types}
            node_ids = {eid for eid, e in model.elements.items() if e.type.lower() in types_set}
        else:
            node_ids = set(model.elements.keys())
        if len(node_ids) > self._max_nodes:
            raise GraphTooLargeError(
                f"The model contains {len(node_ids)} elements; the graph limit is "
                f"{self._max_nodes}. Provide a folder or a root element instead.",
            )
        edges = {}
        for rel in model.relationships.values():
            if rel.source in node_ids and rel.target in node_ids:
                edges[rel.id] = rel
        return self._payload(model, node_ids, edges, root=None, truncated=False)

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #
    def _adjacency(
        self,
        model: Model,
        rel_filter: set[str] | None,
    ) -> dict[str, list[tuple[Any, str]]]:
        """Build a bidirectional adjacency list of (relationship, neighbor)."""
        adjacency: dict[str, list[tuple[Any, str]]] = {}
        for rel in model.relationships.values():
            if rel_filter is not None and rel.type.lower() not in rel_filter:
                continue
            adjacency.setdefault(rel.source, []).append((rel, rel.target))
            adjacency.setdefault(rel.target, []).append((rel, rel.source))
        return adjacency

    def _folder_element_ids(self, model: Model, folder_id: str) -> set[str]:
        """All element ids of a folder including nested sub-folders."""
        result: set[str] = set()
        stack = [folder_id]
        while stack:
            current = stack.pop()
            folder = model.folders.get(current)
            if folder is None:
                continue
            result.update(eid for eid in folder.element_ids if eid in model.elements)
            stack.extend(
                fid for fid, f in model.folders.items() if f.parent_id == current
            )
        return result

    def _payload(
        self,
        model: Model,
        node_ids: set[str],
        edges: dict[str, Any],
        *,
        root: str | None,
        truncated: bool,
    ) -> GraphPayload:
        nodes = [
            GraphNode(
                id=eid,
                name=model.elements[eid].name,
                type=model.elements[eid].type,
                stereotypes=list(model.elements[eid].stereotypes),
                folder_id=model.elements[eid].folder_id,
            )
            for eid in sorted(node_ids, key=lambda e: (model.elements[e].name.lower(), e))
        ]
        edge_list = [
            GraphEdge(
                id=rel.id,
                source=rel.source,
                target=rel.target,
                type=rel.type,
                aggregation=rel.aggregation,
            )
            for rid, rel in sorted(edges.items(), key=lambda kv: kv[1].id)
            if rel.source in node_ids and rel.target in node_ids
        ]
        return GraphPayload(
            model_id=model.model_id,
            nodes=nodes,
            edges=edge_list,
            truncated=truncated,
            root=root,
        )
