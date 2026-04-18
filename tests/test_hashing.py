"""Tests for `keep.utils.hashing`."""

from __future__ import annotations

from keep.utils.hashing import (
    MEANINGFUL_FIELDS,
    content_hash,
    meaningful_hash,
)


class TestContentHash:
    """Tests for `content_hash`."""

    def test_returns_eight_character_hex_string(self) -> None:
        result = content_hash({"slug": "ragu", "status": "draft"})

        assert len(result) == 8
        assert all(c in "0123456789abcdef" for c in result)

    def test_same_dict_produces_same_hash(self) -> None:
        data = {"slug": "ragu", "status": "draft", "kind": "recipe"}

        assert content_hash(data) == content_hash(data)

    def test_different_values_produce_different_hashes(self) -> None:
        a = {"slug": "ragu", "status": "draft"}
        b = {"slug": "ragu", "status": "published"}

        assert content_hash(a) != content_hash(b)

    def test_key_order_does_not_affect_hash(self) -> None:
        a = {"slug": "ragu", "status": "draft"}
        b = {"status": "draft", "slug": "ragu"}

        assert content_hash(a) == content_hash(b)

    def test_extra_field_changes_hash(self) -> None:
        a = {"slug": "ragu"}
        b = {"slug": "ragu", "tags": ["italian"]}

        assert content_hash(a) != content_hash(b)

    def test_empty_dict_does_not_raise(self) -> None:
        result = content_hash({})

        assert len(result) == 8


class TestMeaningfulHash:
    """Tests for `meaningful_hash`."""

    def test_returns_eight_character_hex_string(self) -> None:
        result = meaningful_hash({"status": "draft", "kind": "recipe"}, [])

        assert len(result) == 8
        assert all(c in "0123456789abcdef" for c in result)

    def test_only_meaningful_fields_are_considered(self) -> None:
        base = {"status": "draft", "kind": "recipe", "title": "Ragù"}
        without_title = {"status": "draft", "kind": "recipe"}

        assert meaningful_hash(base, []) == meaningful_hash(without_title, [])

    def test_status_change_changes_hash(self) -> None:
        draft = {"status": "draft", "kind": "recipe"}
        published = {"status": "published", "kind": "recipe"}

        assert meaningful_hash(draft, []) != meaningful_hash(published, [])

    def test_kind_change_changes_hash(self) -> None:
        recipe = {"status": "draft", "kind": "recipe"}
        note = {"status": "draft", "kind": "note"}

        assert meaningful_hash(recipe, []) != meaningful_hash(note, [])

    def test_extension_field_included_when_provided(self) -> None:
        without_ext = {"status": "draft", "kind": "person"}
        with_ext = {"status": "draft", "kind": "person", "birth_date": "1924-04-15"}

        assert meaningful_hash(without_ext, ["birth_date"]) != meaningful_hash(
            with_ext, ["birth_date"]
        )

    def test_extension_field_ignored_when_not_in_extension_list(self) -> None:
        without = {"status": "draft", "kind": "recipe"}
        with_birth = {"status": "draft", "kind": "recipe", "birth_date": "1924-04-15"}

        assert meaningful_hash(without, []) == meaningful_hash(with_birth, [])

    def test_cosmetic_fields_do_not_affect_hash(self) -> None:
        a = {"status": "draft", "kind": "recipe", "summary": "Old summary"}
        b = {"status": "draft", "kind": "recipe", "summary": "New summary"}

        assert meaningful_hash(a, []) == meaningful_hash(b, [])

    def test_meaningful_fields_constant_contains_expected_keys(self) -> None:
        assert "status" in MEANINGFUL_FIELDS
        assert "kind" in MEANINGFUL_FIELDS
        assert "relations" in MEANINGFUL_FIELDS
