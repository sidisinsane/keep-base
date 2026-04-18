"""Tests for `keep.settings`."""

from __future__ import annotations

from pathlib import Path

import pytest

from keep.settings import (
    CONFIG_FILENAME,
    KEEP_DIRNAME,
    SchemaVersionError,
    Settings,
    _deep_merge,
)


class TestDeepMerge:
    """Unit tests for the `_deep_merge` helper."""

    def test_override_takes_precedence(self) -> None:
        result = _deep_merge({"a": 1}, {"a": 2})

        assert result["a"] == 2

    def test_base_keys_preserved_when_not_overridden(self) -> None:
        result = _deep_merge({"a": 1, "b": 2}, {"a": 99})

        assert result["b"] == 2

    def test_nested_dicts_merged_recursively(self) -> None:
        base = {"staleness": {"draft": {"days": 14}, "review": {"days": 28}}}
        override = {"staleness": {"draft": {"days": 7}}}
        result = _deep_merge(base, override)

        assert result["staleness"]["draft"]["days"] == 7
        assert result["staleness"]["review"]["days"] == 28

    def test_lists_replaced_not_merged(self) -> None:
        base = {"required_fields": ["kind", "tags"]}
        override = {"required_fields": ["kind"]}
        result = _deep_merge(base, override)

        assert result["required_fields"] == ["kind"]

    def test_neither_input_is_mutated(self) -> None:
        base = {"a": {"b": 1}}
        override = {"a": {"b": 2}}
        _deep_merge(base, override)

        assert base["a"]["b"] == 1
        assert override["a"]["b"] == 2

    def test_empty_override_returns_copy_of_base(self) -> None:
        base = {"a": 1, "b": 2}
        result = _deep_merge(base, {})

        assert result == base
        assert result is not base

    def test_empty_base_returns_copy_of_override(self) -> None:
        override = {"a": 1}
        result = _deep_merge({}, override)

        assert result == override
        assert result is not override


class TestSettingsLoad:
    """Tests for `Settings.load`."""

    def test_loads_from_valid_workspace(self, workspace: Path) -> None:
        s = Settings.load(workspace)

        assert s.workspace == workspace

    def test_derived_paths_are_correct(self, workspace: Path) -> None:
        s = Settings.load(workspace)

        assert s.keep_dir == workspace / KEEP_DIRNAME
        assert s.config_path == workspace / CONFIG_FILENAME
        assert s.graph_path == workspace / KEEP_DIRNAME / "graph.json"
        assert s.state_path == workspace / KEEP_DIRNAME / "state.json"
        assert s.index_path == workspace / "index.md"

    def test_workspace_values_loaded(self, workspace: Path) -> None:
        s = Settings.load(workspace)

        # Values come from tests/fixtures/workspace/keep.yml,
        # which intentionally overrides the app defaults.
        assert s.staleness.draft == 7
        assert s.staleness.review == 14
        assert s.staleness.published == 90
        assert s.staleness.canon is None
        assert s.completeness.min_ratio == 0.7

    def test_workspace_overrides_staleness(self, workspace: Path) -> None:
        config = workspace / CONFIG_FILENAME
        config.write_text(
            "schema_version: 1\nstaleness:\n  draft:\n    days: 3\n"
        )

        s = Settings.load(workspace)

        assert s.staleness.draft == 3
        assert s.staleness.review == 28

    def test_workspace_overrides_completeness(self, workspace: Path) -> None:
        config = workspace / CONFIG_FILENAME
        config.write_text(
            "schema_version: 1\ncompleteness:\n  min_ratio: 0.9\n"
        )

        s = Settings.load(workspace)

        assert s.completeness.min_ratio == 0.9

    def test_raises_when_config_missing(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="keep.yml"):
            Settings.load(tmp_path)

    def test_raises_on_missing_schema_version(self, workspace: Path) -> None:
        config = workspace / CONFIG_FILENAME
        config.write_text("staleness:\n  draft:\n    days: 7\n")

        with pytest.raises(SchemaVersionError, match="schema_version"):
            Settings.load(workspace)

    def test_raises_on_wrong_schema_version(self, workspace: Path) -> None:
        config = workspace / CONFIG_FILENAME
        config.write_text("schema_version: 99\n")

        with pytest.raises(SchemaVersionError, match="99"):
            Settings.load(workspace)

    def test_schema_is_loaded(self, workspace: Path) -> None:
        s = Settings.load(workspace)

        assert "core" in s.schema
        assert "statuses" in s.schema

    def test_app_extensions_present_by_default(self, workspace: Path) -> None:
        s = Settings.load(workspace)

        assert "genealogy" in s.extensions
        assert "experiment" in s.extensions

    def test_workspace_can_override_extensions(self, workspace: Path) -> None:
        config = workspace / CONFIG_FILENAME
        config.write_text(
            "schema_version: 1\n"
            "extensions:\n"
            "  custom:\n"
            "    applies_when:\n"
            "      kind: custom\n"
            "    additional_required: [my_field]\n"
            "    fields:\n"
            "      my_field: {type: string}\n"
        )

        s = Settings.load(workspace)

        assert "custom" in s.extensions
