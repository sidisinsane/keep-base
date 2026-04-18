"""Tests for `keep.index`."""

from __future__ import annotations

from pathlib import Path

from keep.index import _COLUMNS, _HEADER_COMMENT, IndexRow, build, write
from keep.settings import Settings


class TestBuild:
    """Tests for `index.build`."""

    def test_returns_one_row_per_non_private_document(
        self, settings: Settings
    ) -> None:
        rows = build(settings)

        # workspace has 4 documents, none private
        assert len(rows) == 4

    def test_rows_sorted_alphabetically_by_slug(
        self, settings: Settings
    ) -> None:
        rows = build(settings)
        slugs = [r.slug for r in rows]

        assert slugs == sorted(slugs)

    def test_row_has_all_required_fields(self, settings: Settings) -> None:
        rows = build(settings)
        ragu = next(r for r in rows if r.slug == "ragu")

        assert ragu.slug == "ragu"
        assert ragu.title == "Ragù alla Bolognese"
        assert ragu.kind == "recipe"
        assert ragu.status == "published"
        assert "Bolognese" in ragu.summary

    def test_missing_summary_becomes_empty_string(
        self, workspace: Path, settings: Settings
    ) -> None:
        draft_path = workspace / "drafts" / "unfinished-idea.md"
        content = draft_path.read_text(encoding="utf-8")
        draft_path.write_text(
            content.replace(
                "summary: A half-formed thought about pasta shapes and sauce "
                "viscosity.",
                "",
            ),
            encoding="utf-8",
        )

        rows = build(settings)
        draft = next(r for r in rows if r.slug == "unfinished-idea")

        assert draft.summary == ""

    def test_excludes_private_documents(
        self, workspace: Path, settings: Settings
    ) -> None:
        ragu_path = workspace / "recipes" / "ragu.md"
        content = ragu_path.read_text(encoding="utf-8")
        ragu_path.write_text(
            content.replace("kind: recipe", "kind: recipe\nprivate: true"),
            encoding="utf-8",
        )

        rows = build(settings)
        slugs = [r.slug for r in rows]

        assert "ragu" not in slugs

    def test_excludes_index_md_itself(
        self, workspace: Path, settings: Settings
    ) -> None:
        settings.index_path.write_text(
            "---\n"
            "slug: index\n"
            "title: Index\n"
            "kind: note\n"
            "status: draft\n"
            "date_created: '2026-01-01'\n"
            "tags: []\n"
            "---\n",
            encoding="utf-8",
        )

        rows = build(settings)
        slugs = [r.slug for r in rows]

        assert "index" not in slugs

    def test_excludes_files_inside_keep_dir(
        self, workspace: Path, settings: Settings
    ) -> None:
        keep_dir = workspace / ".keep"
        keep_dir.mkdir(exist_ok=True)
        (keep_dir / "internal.md").write_text(
            "---\n"
            "slug: internal\n"
            "title: Internal\n"
            "kind: note\n"
            "status: draft\n"
            "date_created: '2026-01-01'\n"
            "tags: []\n"
            "---\n",
            encoding="utf-8",
        )

        rows = build(settings)
        slugs = [r.slug for r in rows]

        assert "internal" not in slugs

    def test_skips_malformed_documents_without_aborting(
        self, workspace: Path, settings: Settings
    ) -> None:
        (workspace / "bad.md").write_text(
            "# No frontmatter\n", encoding="utf-8"
        )

        rows = build(settings)

        assert len(rows) == 4

    def test_returns_index_row_instances(self, settings: Settings) -> None:
        rows = build(settings)

        assert all(isinstance(r, IndexRow) for r in rows)


class TestWrite:
    """Tests for `index.write`."""

    def test_writes_index_md_to_workspace_root(
        self, settings: Settings
    ) -> None:
        rows = build(settings)
        output = write(rows, settings)

        assert output == settings.index_path
        assert output.exists()

    def test_output_starts_with_header_comment(
        self, settings: Settings
    ) -> None:
        rows = build(settings)
        write(rows, settings)
        content = settings.index_path.read_text(encoding="utf-8")

        assert content.startswith(_HEADER_COMMENT)

    def test_output_contains_column_headers(self, settings: Settings) -> None:
        rows = build(settings)
        write(rows, settings)
        content = settings.index_path.read_text(encoding="utf-8")

        for col in _COLUMNS:
            assert col in content

    def test_output_contains_all_slugs(self, settings: Settings) -> None:
        rows = build(settings)
        write(rows, settings)
        content = settings.index_path.read_text(encoding="utf-8")

        for row in rows:
            assert row.slug in content

    def test_output_contains_separator_row(self, settings: Settings) -> None:
        rows = build(settings)
        write(rows, settings)
        content = settings.index_path.read_text(encoding="utf-8")

        assert "|---" in content or "| ---" in content

    def test_overwrites_existing_index(self, settings: Settings) -> None:
        settings.index_path.write_text("old content", encoding="utf-8")

        rows = build(settings)
        write(rows, settings)
        content = settings.index_path.read_text(encoding="utf-8")

        assert "old content" not in content
        assert _HEADER_COMMENT in content

    def test_empty_rows_writes_header_only(self, settings: Settings) -> None:
        write([], settings)
        content = settings.index_path.read_text(encoding="utf-8")

        assert _HEADER_COMMENT in content
        assert "slug" in content

    def test_returns_path_to_written_file(self, settings: Settings) -> None:
        rows = build(settings)
        output = write(rows, settings)

        assert output == settings.index_path
