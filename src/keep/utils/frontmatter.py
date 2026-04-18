"""Frontmatter parsing for Keep documents.

Provides utilities for extracting and validating YAML frontmatter from
Markdown files. Frontmatter is defined as a YAML block delimited by `---`
at the start of the file.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML


_yaml = YAML()
_yaml.preserve_quotes = True

FRONTMATTER_DELIMITER = "---"


@dataclass
class Relation:
    """A typed directed edge from one document to another.

    Attributes:
        target: Slug of the target document.
        type: Semantic type of the relation.
        auto_injected: True if this relation was written by the tool rather
            than authored by a human or LLM.
    """

    target: str
    type: str
    auto_injected: bool = False


@dataclass
class Frontmatter:
    """Parsed frontmatter for a single Keep document.

    Only fields relevant to the tool layer are represented as typed
    attributes. All remaining frontmatter keys are preserved in ``extra``
    so that round-trip writes never discard author-provided metadata.

    Attributes:
        slug: Unique identifier for the document.
        title: Human-readable title.
        date_created: ISO 8601 creation date string.
        status: Lifecycle status. One of: draft, review, published, canon.
        tags: List of freeform tags.
        kind: Semantic document kind (e.g. recipe, person, experiment).
        private: Whether the document is private. Defaults to False.
        summary: One-line summary used by the tool to populate index.md.
        relations: Typed edges to other documents.
        extra: Any frontmatter keys not explicitly modelled above.
        source_path: Path to the originating Markdown file.
    """

    slug: str
    title: str
    date_created: str
    status: str
    tags: list[str]
    kind: str
    private: bool = False
    summary: str | None = None
    relations: list[Relation] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)
    source_path: Path | None = None


class FrontmatterError(Exception):
    """Raised when frontmatter cannot be parsed or is structurally invalid."""


def parse(path: Path) -> Frontmatter:
    """Parse the YAML frontmatter of a Markdown file.

    Args:
        path: Path to the Markdown file.

    Returns:
        A :class:`Frontmatter` instance populated from the file.

    Raises:
        FrontmatterError: If the file has no frontmatter block, the YAML is
            malformed, or any required field is missing.
    """
    raw = _extract_raw(path)
    data = _parse_yaml(raw, path)
    return _build(data, path)


def _extract_raw(path: Path) -> str:
    """Return the raw YAML string between the opening ``---`` delimiters.

    Args:
        path: Path to the Markdown file.

    Returns:
        Raw YAML string.

    Raises:
        FrontmatterError: If the file does not begin with a frontmatter block.
    """
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    if not lines or lines[0].strip() != FRONTMATTER_DELIMITER:
        raise FrontmatterError(f"{path}: no frontmatter block found")

    closing = next(
        (
            i
            for i, line in enumerate(lines[1:], start=1)
            if line.strip() == FRONTMATTER_DELIMITER
        ),
        None,
    )

    if closing is None:
        raise FrontmatterError(f"{path}: frontmatter block is not closed")

    return "\n".join(lines[1:closing])


def _parse_yaml(raw: str, path: Path) -> dict[str, Any]:
    """Parse a raw YAML string into a dictionary.

    Args:
        raw: Raw YAML string.
        path: Source path, used only for error messages.

    Returns:
        Parsed YAML as a plain dictionary.

    Raises:
        FrontmatterError: If the YAML is malformed or does not parse to a
            mapping.
    """
    try:
        data = _yaml.load(raw)
    except Exception as exc:
        raise FrontmatterError(f"{path}: YAML parse error: {exc}") from exc

    if not isinstance(data, dict):
        raise FrontmatterError(f"{path}: frontmatter must be a YAML mapping")

    return dict(data)


def _build(data: dict[str, Any], path: Path) -> Frontmatter:
    """Build a :class:`Frontmatter` instance from a parsed YAML dictionary.

    Args:
        data: Parsed frontmatter dictionary.
        path: Source path attached to the returned instance.

    Returns:
        Populated :class:`Frontmatter`.

    Raises:
        FrontmatterError: If any required field is absent.
    """
    required = ("slug", "title", "date_created", "status", "tags", "kind")
    missing = [f for f in required if f not in data]
    if missing:
        raise FrontmatterError(
            f"{path}: missing required field(s): {', '.join(missing)}"
        )

    known = {
        "slug",
        "title",
        "date_created",
        "status",
        "tags",
        "kind",
        "private",
        "summary",
        "relations",
    }

    return Frontmatter(
        slug=data["slug"],
        title=data["title"],
        date_created=data["date_created"],
        status=data["status"],
        tags=list(data["tags"]),
        kind=data["kind"],
        private=bool(data.get("private", False)),
        summary=data.get("summary"),
        relations=_parse_relations(data.get("relations") or [], path),
        extra={k: v for k, v in data.items() if k not in known},
        source_path=path,
    )


def _parse_relations(raw: list[Any], path: Path) -> list[Relation]:
    """Parse a list of raw relation mappings into :class:`Relation` instances.

    Args:
        raw: List of relation dicts from frontmatter.
        path: Source path, used only for error messages.

    Returns:
        List of :class:`Relation` instances.

    Raises:
        FrontmatterError: If any relation entry is missing ``target`` or
            ``type``.
    """
    relations = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            raise FrontmatterError(f"{path}: relation[{i}] must be a mapping")
        if "target" not in item or "type" not in item:
            raise FrontmatterError(
                f"{path}: relation[{i}] must have 'target' and 'type'"
            )
        relations.append(
            Relation(
                target=item["target"],
                type=item["type"],
                auto_injected=bool(item.get("auto_injected", False)),
            )
        )
    return relations
