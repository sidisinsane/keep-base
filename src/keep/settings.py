"""Settings for Keep.

Loads and merges configuration from two sources:

1. `keep/data/schema.yml` — immutable app schema, bundled with the package.
2. `keep/data/keep.yml` — app defaults for workspace configuration.
3. `<workspace>/keep.yml` — user overrides, merged on top of app defaults.

The merge order is: app defaults < workspace overrides. The schema is never
merged — it is always loaded from the app bundle and treated as immutable.

Typical usage::

    from keep.settings import Settings

    settings = Settings.load(workspace)
    print(settings.keep_dir)
"""

from __future__ import annotations

import copy

from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML


_yaml = YAML()

# ---------------------------------------------------------------------------
# File and directory names — defined once, imported everywhere
# ---------------------------------------------------------------------------

CONFIG_FILENAME = "keep.yml"
KEEP_DIRNAME = ".keep"
GRAPH_FILENAME = "graph.json"
STATE_FILENAME = "state.json"
INDEX_FILENAME = "index.md"

# ---------------------------------------------------------------------------
# Schema version — must match schema.yml and workspace keep.yml
# ---------------------------------------------------------------------------

SUPPORTED_SCHEMA_VERSION = 1


class SchemaVersionError(Exception):
    """Raised when keep.yml declares unsupported / mismatched schema version."""


@dataclass
class StalenessSettings:
    """Staleness thresholds per document status.

    A value of `None` means the status never triggers a staleness flag.

    Attributes:
        draft: Days before a draft document is considered stale.
        review: Days before a review document is considered stale.
        published: Days before a published document is considered stale.
        canon: Days before a canon document is considered stale (None = never).
    """

    draft: int = 14
    review: int = 28
    published: int = 180
    canon: int | None = None


@dataclass
class CompletenessSettings:
    """Completeness scoring thresholds.

    Attributes:
        min_ratio: Minimum ratio of populated recommended fields below which
            a document is flagged regardless of age.
        required_fields: Fields that must be present for a document to be
            considered complete.
        required_relations: Minimum number of relations a document must have
            to be considered complete.
    """

    min_ratio: float = 0.6
    required_fields: list[str] = field(default_factory=lambda: ["kind", "tags"])
    required_relations: int = 1


@dataclass
class Settings:
    """Runtime settings for a Keep workspace.

    Combines path constants derived from the workspace root with configuration
    merged from app defaults and the workspace `keep.yml`. The raw schema
    is also exposed for use by the linter and other tools.

    Consumers should always obtain a `Settings` instance via :meth:`load`
    rather than constructing one directly.

    Attributes:
        workspace: Absolute path to the workspace root directory.
        keep_dir: Absolute path to the `.keep/` directory.
        config_path: Absolute path to `keep.yml`.
        graph_path: Absolute path to `.keep/graph.json`.
        state_path: Absolute path to `.keep/state.json`.
        index_path: Absolute path to `index.md` at the workspace root.
        staleness: Staleness threshold configuration.
        completeness: Completeness scoring configuration.
        extensions: Extension definitions merged from app defaults & workspace.
        schema: Raw schema dictionary loaded from `data/schema.yml`.
    """

    workspace: Path
    keep_dir: Path
    config_path: Path
    graph_path: Path
    state_path: Path
    index_path: Path
    staleness: StalenessSettings = field(default_factory=StalenessSettings)
    completeness: CompletenessSettings = field(
        default_factory=CompletenessSettings
    )
    extensions: dict[str, Any] = field(default_factory=dict)
    schema: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load(cls, workspace: Path) -> Settings:
        """Load and merge settings for the given workspace.

        Merge order: app defaults < workspace `keep.yml`. The schema is
        loaded separately and never merged.

        Args:
            workspace: Absolute path to the workspace root directory.

        Returns:
            Populated :class:`Settings` instance.

        Raises:
            FileNotFoundError: If `keep.yml` does not exist at the workspace
                root.
            SchemaVersionError: If the workspace `keep.yml` declares a
                `schema_version` that does not match the app schema.
        """
        schema = _load_bundled("schema.yml")
        _validate_schema_version(schema, source="data/schema.yml")

        app_defaults = _load_bundled("keep.yml")
        _validate_schema_version(app_defaults, source="data/keep.yml")

        config_path = workspace / CONFIG_FILENAME
        if not config_path.exists():
            raise FileNotFoundError(
                f"{CONFIG_FILENAME} not found in {workspace}"
            )

        workspace_config = _yaml.load(config_path) or {}
        _validate_schema_version(workspace_config, source=str(config_path))

        merged = _deep_merge(app_defaults, workspace_config)

        return cls(
            workspace=workspace,
            keep_dir=workspace / KEEP_DIRNAME,
            config_path=config_path,
            graph_path=workspace / KEEP_DIRNAME / GRAPH_FILENAME,
            state_path=workspace / KEEP_DIRNAME / STATE_FILENAME,
            index_path=workspace / INDEX_FILENAME,
            staleness=_load_staleness(merged.get("staleness", {})),
            completeness=_load_completeness(merged.get("completeness", {})),
            extensions=merged.get("extensions", {}),
            schema=schema,
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _load_bundled(filename: str) -> dict[str, Any]:
    """Load a YAML file bundled in `keep/data/`.

    Args:
        filename: Filename within the `keep.data` package (e.g.
            `"schema.yml"`).

    Returns:
        Parsed YAML as a plain dictionary.
    """
    package = resources.files("keep.data")
    text = (package / filename).read_text(encoding="utf-8")
    return dict(_yaml.load(text) or {})


def _validate_schema_version(config: dict[str, Any], source: str) -> None:
    """Assert that a config dictionary declares the supported schema version.

    Args:
        config: Parsed YAML dictionary to check.
        source: Human-readable source name used in error messages.

    Raises:
        SchemaVersionError: If `schema_version` is missing or does not match
            :data:`SUPPORTED_SCHEMA_VERSION`.
    """
    version = config.get("schema_version")
    if version is None:
        raise SchemaVersionError(
            f"{source}: missing required field 'schema_version'"
        )
    if version != SUPPORTED_SCHEMA_VERSION:
        raise SchemaVersionError(
            f"{source}: schema_version {version} is not supported "
            f"(expected {SUPPORTED_SCHEMA_VERSION})"
        )


def _deep_merge(
    base: dict[str, Any], override: dict[str, Any]
) -> dict[str, Any]:
    """Recursively merge two dictionaries, with override taking precedence.

    Mapping values are merged recursively. All other types — including lists —
    are replaced wholesale by the override value. This matches the intended
    behaviour for `keep.yml`: a workspace that specifies `required_fields`
    replaces the app default list entirely rather than appending to it.

    Args:
        base: Base dictionary (app defaults).
        override: Override dictionary (workspace config).

    Returns:
        New merged dictionary. Neither input is mutated.
    """
    result = copy.deepcopy(base)
    for key, value in override.items():
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(value, dict)
        ):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def _load_staleness(raw: dict) -> StalenessSettings:
    """Build :class:`StalenessSettings` from a raw config dictionary.

    Args:
        raw: The `staleness` block from the merged config, or an empty dict.

    Returns:
        Populated :class:`StalenessSettings`.
    """
    defaults = StalenessSettings()
    return StalenessSettings(
        draft=raw.get("draft", {}).get("days", defaults.draft),
        review=raw.get("review", {}).get("days", defaults.review),
        published=raw.get("published", {}).get("days", defaults.published),
        canon=raw.get("canon", {}).get("days", defaults.canon),
    )


def _load_completeness(raw: dict) -> CompletenessSettings:
    """Build :class:`CompletenessSettings` from a raw config dictionary.

    Args:
        raw: The `completeness` block from the merged config, or an empty dict.

    Returns:
        Populated :class:`CompletenessSettings`.
    """
    defaults = CompletenessSettings()
    return CompletenessSettings(
        min_ratio=raw.get("min_ratio", defaults.min_ratio),
        required_fields=raw.get("required_fields", defaults.required_fields),
        required_relations=raw.get(
            "required_relations", defaults.required_relations
        ),
    )
