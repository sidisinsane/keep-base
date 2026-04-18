"""Tests for `keep.utils.extensions`."""

from __future__ import annotations

import pytest

from keep.utils.extensions import fields_for_kind, required_for_kind


_EXTENSIONS = {
    "genealogy": {
        "applies_when": {"kind": "person"},
        "additional_required": ["birth_date", "family_name"],
        "fields": {
            "birth_date": {"type": "isodate"},
            "death_date": {"type": "isodate"},
            "family_name": {"type": "string"},
        },
    },
    "experiment": {
        "applies_when": {"kind": "experiment"},
        "additional_required": ["hypothesis", "outcome"],
        "fields": {
            "hypothesis": {"type": "string"},
            "outcome": {"type": "string"},
        },
    },
}


class TestFieldsForKind:
    """Tests for `fields_for_kind`."""

    def test_returns_all_fields_for_matching_kind(self) -> None:
        result = fields_for_kind("person", _EXTENSIONS)

        assert set(result) == {"birth_date", "death_date", "family_name"}

    def test_returns_empty_for_non_matching_kind(self) -> None:
        result = fields_for_kind("recipe", _EXTENSIONS)

        assert result == []

    def test_returns_empty_for_empty_extensions(self) -> None:
        result = fields_for_kind("person", {})

        assert result == []

    def test_does_not_mix_fields_from_other_extensions(self) -> None:
        result = fields_for_kind("experiment", _EXTENSIONS)

        assert "birth_date" not in result
        assert "hypothesis" in result

    def test_multiple_matching_extensions_combined(self) -> None:
        extensions = {
            "ext_a": {
                "applies_when": {"kind": "custom"},
                "additional_required": [],
                "fields": {"field_a": {"type": "string"}},
            },
            "ext_b": {
                "applies_when": {"kind": "custom"},
                "additional_required": [],
                "fields": {"field_b": {"type": "string"}},
            },
        }

        result = fields_for_kind("custom", extensions)

        assert set(result) == {"field_a", "field_b"}


class TestRequiredForKind:
    """Tests for `required_for_kind`."""

    def test_returns_required_fields_for_matching_kind(self) -> None:
        result = required_for_kind("person", _EXTENSIONS)

        assert set(result) == {"birth_date", "family_name"}

    def test_does_not_return_optional_fields(self) -> None:
        result = required_for_kind("person", _EXTENSIONS)

        assert "death_date" not in result

    def test_returns_empty_for_non_matching_kind(self) -> None:
        result = required_for_kind("recipe", _EXTENSIONS)

        assert result == []

    def test_returns_empty_for_empty_extensions(self) -> None:
        result = required_for_kind("person", {})

        assert result == []

    def test_experiment_required_fields(self) -> None:
        result = required_for_kind("experiment", _EXTENSIONS)

        assert set(result) == {"hypothesis", "outcome"}
