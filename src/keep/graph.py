"""Graph generation for Keep.

Walks the wiki directory, parses all Markdown documents, and writes a
deterministic `graph.json` to the `.keep/` folder. The graph captures
every document as a node and every frontmatter relation as a typed directed
edge.

The output is intentionally minimal — it is a derived artefact rebuilt on
every run, not a source of truth.
"""

from __future__ import annotations

import json

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from keep.logging import get_logger
from keep.settings import Settings
from keep.utils.frontmatter import Frontmatter, FrontmatterError, parse


log = get_logger(__name__)


def build(settings: Settings) -> dict[str, Any]:
    """Build the graph data structure from all documents in the wiki.

    Skips files that fail frontmatter parsing and logs a warning for each,
    so a single malformed document does not abort the entire run.

    Args:
        settings: Resolved wiki settings.

    Returns:
        Graph dictionary with `generated_at`, `nodes`, and `edges` keys.
    """
    nodes = []
    edges = []

    for path in sorted(settings.workspace.rglob("*.md")):
        if _is_ignored(path, settings):
            continue

        try:
            doc = parse(path)
        except FrontmatterError as exc:
            log.warning(
                "skipping %s: %s", path.relative_to(settings.workspace), exc
            )
            continue

        nodes.append(_node(doc))
        edges.extend(_edges(doc))

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "nodes": nodes,
        "edges": edges,
    }


def write(graph: dict[str, Any], settings: Settings) -> Path:
    """Write the graph to `.keep/graph.json`.

    Creates the `.keep/` directory if it does not exist.

    Args:
        graph: Graph dictionary as returned by :func:`build`.
        settings: Resolved wiki settings.

    Returns:
        Path to the written file.
    """
    settings.keep_dir.mkdir(exist_ok=True)
    settings.graph_path.write_text(
        json.dumps(graph, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return settings.graph_path


def _node(doc: Frontmatter) -> dict[str, Any]:
    """Build a graph node from a parsed document.

    Args:
        doc: Parsed frontmatter.

    Returns:
        Node dictionary.
    """
    return {
        "slug": doc.slug,
        "title": doc.title,
        "kind": doc.kind,
        "status": doc.status,
        "private": doc.private,
    }


def _edges(doc: Frontmatter) -> list[dict[str, Any]]:
    """Build graph edges from a document's relations.

    Args:
        doc: Parsed frontmatter.

    Returns:
        List of edge dictionaries.
    """
    return [
        {
            "from": doc.slug,
            "to": relation.target,
            "type": relation.type,
            "auto_injected": relation.auto_injected,
        }
        for relation in doc.relations
    ]


def _is_ignored(path: Path, settings: Settings) -> bool:
    """Return True if the path should be excluded from the graph.

    Excludes any file inside the `.keep/` directory itself.

    Args:
        path: Candidate file path.
        settings: Resolved wiki settings.

    Returns:
        True if the file should be skipped.
    """
    return settings.keep_dir.name in path.relative_to(settings.workspace).parts
