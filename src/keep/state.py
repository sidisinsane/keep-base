# pylint: disable=broad-exception-caught
"""State store management for Keep.

Maintains `.keep/state.json` — a tool-owned record of each document's last
meaningful modification timestamp and frontmatter hashes. This is the single
source of truth for staleness tracking.

The state store is never edited by humans or the LLM. It is rebuilt
incrementally on each `keep state` run: unchanged documents are skipped,
cosmetic edits update only the content hash, and meaningful edits reset the
staleness clock.

Typical usage::

    from keep.state import load, update, write

    settings = Settings.load(workspace)
    state = load(settings)
    state = update(state, settings)
    write(state, settings)
"""

from __future__ import annotations

import json

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from keep.logging import get_logger
from keep.settings import Settings
from keep.utils.extensions import fields_for_kind
from keep.utils.frontmatter import FrontmatterError, parse
from keep.utils.hashing import content_hash, meaningful_hash


log = get_logger(__name__)

#: Schema version written to state.json — increment on breaking changes.
STATE_SCHEMA_VERSION = 1


@dataclass
class DocumentState:
    """State record for a single Keep document.

    Attributes:
        last_meaningful_modification: ISO 8601 timestamp of the last change
            that reset the staleness clock.
        content_hash: Hash of the full parsed frontmatter dict. Used to detect
            that anything changed since the last run.
        meaningful_hash: Hash of only the staleness-relevant fields. Changes
            only when the staleness clock should reset.
        status_at_last_check: The document's status as of the last run.
            Allows status-transition detection without re-diffing.
    """

    last_meaningful_modification: str
    content_hash: str
    meaningful_hash: str
    status_at_last_check: str


@dataclass
class State:
    """Full state store for a Keep workspace.

    Attributes:
        schema_version: Version of the state store format.
        generated_at: ISO 8601 timestamp of the last `keep state` run.
        documents: Mapping of slug to per-document state records.
    """

    schema_version: int = STATE_SCHEMA_VERSION
    generated_at: str = ""
    documents: dict[str, DocumentState] = field(default_factory=dict)


def load(settings: Settings) -> State:
    """Load the state store from `.keep/state.json`.

    Returns an empty :class:`State` if the file does not exist or cannot be
    parsed. A missing state file is not an error — it simply means every
    document will be treated as new and seeded from filesystem `mtime`.

    Args:
        settings: Resolved workspace settings.

    Returns:
        Loaded or empty :class:`State` instance.
    """
    if not settings.state_path.exists():
        return State()

    try:
        raw = json.loads(settings.state_path.read_text(encoding="utf-8"))
        return _deserialise(raw)
    except Exception as exc:
        log.warning("could not load state.json, starting fresh: %s", exc)
        return State()


def update(state: State, settings: Settings) -> State:
    """Update the state store by walking all workspace documents.

    For each document:

    - If no state record exists, seed it from filesystem `mtime`.
    - If `content_hash` is unchanged, skip the document entirely.
    - If `content_hash` changed but `meaningful_hash` did not, update
      `content_hash` and `status_at_last_check` only — the staleness clock
      is not reset.
    - If `meaningful_hash` changed, reset `last_meaningful_modification` to
      now and update all fields.

    Documents that fail frontmatter parsing are skipped with a warning.

    Args:
        state: Existing state, as returned by :func:`load`.
        settings: Resolved workspace settings.

    Returns:
        Updated :class:`State` instance. The input is not mutated.
    """
    keep_dir_name = settings.keep_dir.name
    updated_docs: dict[str, DocumentState] = {}

    for path in sorted(settings.workspace.rglob("*.md")):
        if keep_dir_name in path.relative_to(settings.workspace).parts:
            continue

        try:
            doc = parse(path)
        except FrontmatterError as exc:
            log.warning(
                "skipping %s: %s", path.relative_to(settings.workspace), exc
            )
            continue

        ext_fields = fields_for_kind(doc.kind, settings.extensions)
        c_hash = content_hash(dict(vars(doc)))
        m_hash = meaningful_hash(dict(vars(doc)), ext_fields)

        existing = state.documents.get(doc.slug)

        if existing is None:
            updated_docs[doc.slug] = _seed(path, c_hash, m_hash, doc.status)
            log.debug("new document: %s", doc.slug)

        elif existing.content_hash == c_hash:
            updated_docs[doc.slug] = existing
            log.debug("unchanged: %s", doc.slug)

        elif existing.meaningful_hash == m_hash:
            updated_docs[doc.slug] = DocumentState(
                last_meaningful_modification=existing.last_meaningful_modification,
                content_hash=c_hash,
                meaningful_hash=m_hash,
                status_at_last_check=doc.status,
            )
            log.debug("cosmetic change: %s", doc.slug)

        else:
            updated_docs[doc.slug] = DocumentState(
                last_meaningful_modification=_now(),
                content_hash=c_hash,
                meaningful_hash=m_hash,
                status_at_last_check=doc.status,
            )
            log.debug("meaningful change: %s", doc.slug)

    return State(
        schema_version=STATE_SCHEMA_VERSION,
        generated_at=_now(),
        documents=updated_docs,
    )


def write(state: State, settings: Settings) -> Path:
    """Write the state store to `.keep/state.json`.

    Creates the `.keep/` directory if it does not exist.

    Args:
        state: State to persist.
        settings: Resolved workspace settings.

    Returns:
        Path to the written file.
    """
    settings.keep_dir.mkdir(exist_ok=True)
    settings.state_path.write_text(
        json.dumps(_serialise(state), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return settings.state_path


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _seed(
    path: Path,
    c_hash: str,
    m_hash: str,
    status: str,
) -> DocumentState:
    """Seed a state record for a new document from filesystem mtime.

    Args:
        path: Path to the document file.
        c_hash: Pre-computed content hash.
        m_hash: Pre-computed meaningful hash.
        status: Current document status.

    Returns:
        New :class:`DocumentState` seeded from filesystem mtime.
    """
    mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    return DocumentState(
        last_meaningful_modification=mtime.isoformat(),
        content_hash=c_hash,
        meaningful_hash=m_hash,
        status_at_last_check=status,
    )


def _now() -> str:
    """Return the current UTC time as an ISO 8601 string.

    Returns:
        Current UTC timestamp.
    """
    return datetime.now(timezone.utc).isoformat()


def _serialise(state: State) -> dict[str, Any]:
    """Convert a :class:`State` instance to a JSON-serialisable dictionary.

    Args:
        state: State to serialise.

    Returns:
        Plain dictionary ready for ``json.dumps``.
    """
    return {
        "schema_version": state.schema_version,
        "generated_at": state.generated_at,
        "documents": {
            slug: {
                "last_meaningful_modification": (
                    doc.last_meaningful_modification
                ),
                "content_hash": doc.content_hash,
                "meaningful_hash": doc.meaningful_hash,
                "status_at_last_check": doc.status_at_last_check,
            }
            for slug, doc in state.documents.items()
        },
    }


def _deserialise(raw: dict[str, Any]) -> State:
    """Build a :class:`State` instance from a raw parsed JSON dictionary.

    Args:
        raw: Dictionary as loaded from ``state.json``.

    Returns:
        Populated :class:`State` instance.
    """
    docs = {
        slug: DocumentState(
            last_meaningful_modification=d["last_meaningful_modification"],
            content_hash=d["content_hash"],
            meaningful_hash=d["meaningful_hash"],
            status_at_last_check=d["status_at_last_check"],
        )
        for slug, d in raw.get("documents", {}).items()
    }
    return State(
        schema_version=raw.get("schema_version", STATE_SCHEMA_VERSION),
        generated_at=raw.get("generated_at", ""),
        documents=docs,
    )
