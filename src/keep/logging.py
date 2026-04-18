"""Logging configuration for Keep.

Provides a single :func:`get_logger` function that all Keep modules use to
obtain a logger. Centralising this ensures a consistent format and makes it
easy to adjust verbosity from the CLI without touching individual modules.

Typical usage::

    from keep.logging import get_logger

    log = get_logger(__name__)
    log.warning("skipping %s: %s", path, reason)
"""

from __future__ import annotations

import sys
import logging


_FORMATTER = logging.Formatter(
    fmt="%(levelname)-8s %(name)s: %(message)s",
)

_handler = logging.StreamHandler(sys.stderr)
_handler.setFormatter(_FORMATTER)

_root = logging.getLogger("keep")
_root.addHandler(_handler)
_root.setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return a logger namespaced under the `keep` root logger.

    Args:
        name: Typically `__name__` of the calling module.

    Returns:
        A :class:`logging.Logger` instance.
    """
    return logging.getLogger(name)


def set_verbosity(verbose: bool) -> None:
    """Adjust the log level of the `keep` root logger.

    Called once during CLI startup based on the `--verbose` flag.

    Args:
        verbose: If True, set level to DEBUG; otherwise WARNING.
    """
    _root.setLevel(logging.DEBUG if verbose else logging.WARNING)
