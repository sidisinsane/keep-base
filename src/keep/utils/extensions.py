"""Extension field resolution for Keep documents.

Provides utilities for determining which extension fields apply to a document
based on its `kind` and the active extensions defined in workspace settings.
"""

from __future__ import annotations

from typing import Any


def fields_for_kind(kind: str, extensions: dict[str, Any]) -> list[str]:
    """Return the field names defined by any extension that applies to a kind.

    An extension applies when its `applies_when.kind` matches the document
    kind exactly. All field names from matching extensions are returned as a
    flat list.

    Args:
        kind: The document kind to match against (e.g. ``person``,
            ``experiment``).
        extensions: The extensions mapping from :attr:`Settings.extensions`.

    Returns:
        List of field names contributed by all matching extensions. Empty if
        no extensions apply.
    """
    result = []
    for ext in extensions.values():
        applies_when = ext.get("applies_when", {})
        if applies_when.get("kind") == kind:
            result.extend(ext.get("fields", {}).keys())
    return result


def required_for_kind(kind: str, extensions: dict[str, Any]) -> list[str]:
    """Return field names *required* by any extension that applies to a kind.

    Args:
        kind: The document kind to match against.
        extensions: The extensions mapping from :attr:`Settings.extensions`.

    Returns:
        List of required field names from all matching extensions.
    """
    result = []
    for ext in extensions.values():
        applies_when = ext.get("applies_when", {})
        if applies_when.get("kind") == kind:
            result.extend(ext.get("additional_required", []))
    return result
