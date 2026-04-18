"""Tests for `keep.utils.frontmatter`."""

from __future__ import annotations

from pathlib import Path

import pytest

from keep.utils.frontmatter import Frontmatter, FrontmatterError, parse


class TestParseValid:
    """Parsing well-formed Keep documents."""

    def test_parses_required_fields(self, workspace_dir: Path) -> None:
        path = workspace_dir / "recipes" / "ragu.md"
        doc = parse(path)

        assert doc.slug == "ragu"
        assert doc.title == "Ragù alla Bolognese"
        assert doc.kind == "recipe"
        assert doc.status == "published"
        assert doc.date_created == "2026-01-10"

    def test_parses_tags_as_list(self, workspace_dir: Path) -> None:
        path = workspace_dir / "recipes" / "ragu.md"
        doc = parse(path)

        assert isinstance(doc.tags, list)
        assert "italian" in doc.tags

    def test_parses_summary(self, workspace_dir: Path) -> None:
        path = workspace_dir / "recipes" / "ragu.md"
        doc = parse(path)

        assert doc.summary is not None
        assert "Bolognese" in doc.summary

    def test_parses_relations(self, workspace_dir: Path) -> None:
        path = workspace_dir / "recipes" / "ragu.md"
        doc = parse(path)

        assert len(doc.relations) == 1
        assert doc.relations[0].target == "soffritto"
        assert doc.relations[0].type == "derived_from"
        assert doc.relations[0].auto_injected is False

    def test_parses_auto_injected_relation(self, workspace_dir: Path) -> None:
        path = workspace_dir / "recipes" / "soffritto.md"
        doc = parse(path)

        injected = next(r for r in doc.relations if r.auto_injected)
        assert injected.target == "ragu"
        assert injected.type == "superseded_by"

    def test_private_defaults_to_false(self, workspace_dir: Path) -> None:
        path = workspace_dir / "recipes" / "ragu.md"
        doc = parse(path)

        assert doc.private is False

    def test_source_path_is_set(self, workspace_dir: Path) -> None:
        path = workspace_dir / "recipes" / "ragu.md"
        doc = parse(path)

        assert doc.source_path == path

    def test_extra_fields_preserved(self, workspace_dir: Path) -> None:
        path = workspace_dir / "people" / "marcella-hazan.md"
        doc = parse(path)

        assert "birth_date" in doc.extra
        assert "family_name" in doc.extra
        assert doc.extra["family_name"] == "Hazan"

    def test_no_relations_returns_empty_list(self, workspace_dir: Path) -> None:
        path = workspace_dir / "drafts" / "unfinished-idea.md"
        doc = parse(path)

        assert doc.relations == []

    def test_returns_frontmatter_instance(self, workspace_dir: Path) -> None:
        path = workspace_dir / "recipes" / "ragu.md"
        doc = parse(path)

        assert isinstance(doc, Frontmatter)


class TestParseInvalid:
    """Parsing malformed or structurally invalid documents."""

    def test_raises_on_no_frontmatter(self, invalid_dir: Path) -> None:
        path = invalid_dir / "no-frontmatter.md"

        with pytest.raises(
            FrontmatterError, match="no frontmatter block found"
        ):
            parse(path)

    def test_raises_on_unclosed_frontmatter(self, invalid_dir: Path) -> None:
        path = invalid_dir / "unclosed-frontmatter.md"

        with pytest.raises(FrontmatterError, match="not closed"):
            parse(path)

    def test_raises_on_malformed_yaml(self, invalid_dir: Path) -> None:
        path = invalid_dir / "malformed-yaml.md"

        with pytest.raises(FrontmatterError, match="YAML parse error"):
            parse(path)

    def test_raises_on_missing_required_field(self, invalid_dir: Path) -> None:
        path = invalid_dir / "missing-required-field.md"

        with pytest.raises(FrontmatterError, match="missing required field"):
            parse(path)

    def test_error_message_contains_field_name(self, invalid_dir: Path) -> None:
        path = invalid_dir / "missing-required-field.md"

        with pytest.raises(FrontmatterError, match="kind"):
            parse(path)

    def test_raises_on_nonexistent_file(self, tmp_path: Path) -> None:
        path = tmp_path / "ghost.md"

        with pytest.raises(FileNotFoundError):
            parse(path)

    def test_raises_on_relation_missing_target(self, tmp_path: Path) -> None:
        doc = tmp_path / "bad-relation.md"
        doc.write_text(
            "---\n"
            "slug: bad\n"
            "title: Bad\n"
            "kind: note\n"
            "status: draft\n"
            "date_created: '2026-01-01'\n"
            "tags: [test]\n"
            "relations:\n"
            "  - type: derived_from\n"
            "---\n"
        )

        with pytest.raises(FrontmatterError, match="'target' and 'type'"):
            parse(doc)
