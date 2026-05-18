"""Frontmatter hashing for Keep state tracking.

Provides deterministic hash functions used by the state store to detect
document changes. Two hashes are maintained per document:

- ``content_hash``: hash of the full parsed frontmatter dict. Changes whenever
  any frontmatter field is added, removed, or modified.
- ``meaningful_hash``: hash of only the fields that reset the staleness clock
  (``status``, ``kind``, ``relations``, and active extension fields). Changes
  only on semantically significant edits.
"""

from __future__ import annotations

import json
import hashlib

from typing import Any


#: Core fields whose changes reset the staleness clock.
MEANINGFUL_FIELDS = ["status", "kind", "relations"]


def content_hash(frontmatter: dict[str, Any]) -> str:
    """Compute a hash of the full parsed frontmatter dictionary.

    The dictionary is serialised in a canonical, deterministic order before
    hashing so that key insertion order does not affect the result.

    Args:
        frontmatter: Parsed frontmatter dictionary for a document.

    Returns:
        Eight-character hex digest.
    """
    return _hash_dict(frontmatter)


def meaningful_hash(
    frontmatter: dict[str, Any],
    extension_fields: list[str],
) -> str:
    """Compute a hash of only the fields that affect the staleness clock.

    Only ``status``, ``kind``, ``relations``, and any fields contributed by
    active extensions are included. Cosmetic changes — prose edits, tag
    reordering, summary rewrites — do not affect this hash.

    Args:
        frontmatter: Parsed frontmatter dictionary for a document.
        extension_fields: Field names contributed by extensions active for
            this document's kind. See :func:
            `keep.utils.extensions.fields_for_kind`.

    Returns:
        Eight-character hex digest.
    """
    watched = MEANINGFUL_FIELDS + extension_fields
    subset = {k: frontmatter[k] for k in sorted(watched) if k in frontmatter}
    return _hash_dict(subset)


def _hash_dict(data: dict[str, Any]) -> str:
    """Serialise a dictionary and return an 8-character SHA-256 hex digest.

    Args:
        data: Dictionary to hash.

    Returns:
        Eight-character hex digest.
    """
    serialised = json.dumps(
        data, sort_keys=True, ensure_ascii=False, default=str
    )
    return hashlib.sha256(serialised.encode()).hexdigest()[:8]
