"""Tests for `keep.lint`."""

from __future__ import annotations

import json

from pathlib import Path

from keep.lint import (
    DocumentReport,
    LintReport,
    run,
    write,
)
from keep.settings import Settings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_doc(
    path: Path, slug: str, status: str = "draft", **kwargs: str
) -> None:
    """Write a minimal valid document to a path.

    Args:
        path: File path to write.
        slug: Document slug.
        status: Lifecycle status.
        **kwargs: Additional frontmatter fields as key=value strings.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    extra = "".join(f"\n{k}: {v}" for k, v in kwargs.items())
    path.write_text(
        f"---\n"
        f"slug: {slug}\n"
        f"title: {slug.title()}\n"
        f"kind: note\n"
        f"status: {status}\n"
        f"date_created: '2026-01-01'\n"
        f"tags: [test]{extra}\n"
        f"---\n",
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Clean workspace
# ---------------------------------------------------------------------------


class TestCleanWorkspace:
    """Linting a workspace with no violations."""

    def test_returns_lint_report(self, settings: Settings) -> None:
        report = run(settings)

        assert isinstance(report, LintReport)

    def test_summary_has_correct_total(self, settings: Settings) -> None:
        report = run(settings)

        assert report.summary.total == 4

    def test_clean_report_has_no_hard_violations(
        self, settings: Settings
    ) -> None:
        report = run(settings)

        assert report.summary.hard_violations == 0

    def test_clean_property_true_when_no_violations(
        self, settings: Settings
    ) -> None:
        report = run(settings)

        assert report.clean is True

    def test_all_documents_present_in_report(self, settings: Settings) -> None:
        report = run(settings)

        assert set(report.documents.keys()) == {
            "ragu",
            "soffritto",
            "marcella-hazan",
            "unfinished-idea",
        }


# ---------------------------------------------------------------------------
# Hard violations
# ---------------------------------------------------------------------------


class TestDanglingSlug:
    """Dangling slug hard violation."""

    def test_flags_relation_to_nonexistent_slug(
        self, workspace: Path, settings: Settings
    ) -> None:
        ragu_path = workspace / "recipes" / "ragu.md"
        content = ragu_path.read_text(encoding="utf-8")
        ragu_path.write_text(
            content.replace(
                "  - target: soffritto\n    type: derived_from",
                "  - target: ghost-doc\n    type: derived_from",
            ),
            encoding="utf-8",
        )

        report = run(settings)

        assert any(
            "dangling_slug" in v
            for v in report.documents["ragu"].hard_violations
        )

    def test_dangling_slug_increments_summary_count(
        self, workspace: Path, settings: Settings
    ) -> None:
        ragu_path = workspace / "recipes" / "ragu.md"
        content = ragu_path.read_text(encoding="utf-8")
        ragu_path.write_text(
            content.replace("target: soffritto", "target: ghost-doc"),
            encoding="utf-8",
        )

        report = run(settings)

        assert report.summary.hard_violations >= 1


class TestPrivateTargetInPublicDoc:
    """Private target in public document hard violation."""

    def test_flags_public_doc_relating_to_private_doc(
        self, workspace: Path, settings: Settings
    ) -> None:
        # Make soffritto private.
        soffritto_path = workspace / "recipes" / "soffritto.md"
        content = soffritto_path.read_text(encoding="utf-8")
        soffritto_path.write_text(
            content.replace("kind: recipe", "kind: recipe\nprivate: true"),
            encoding="utf-8",
        )

        report = run(settings)

        assert any(
            "private_target_in_public_doc" in v
            for v in report.documents["ragu"].hard_violations
        )

    def test_permits_private_doc_relating_to_public(
        self, workspace: Path, settings: Settings
    ) -> None:
        # Make ragu private and relate to soffritto (public) — should be fine.
        ragu_path = workspace / "recipes" / "ragu.md"
        content = ragu_path.read_text(encoding="utf-8")
        ragu_path.write_text(
            content.replace("kind: recipe", "kind: recipe\nprivate: true"),
            encoding="utf-8",
        )

        report = run(settings)

        assert not any(
            "private_target_in_public_doc" in v
            for v in report.documents["ragu"].hard_violations
        )


class TestInvalidPromotion:
    """Invalid promotion hard violation."""

    def test_flags_published_doc_with_dangling_slug(
        self, workspace: Path, settings: Settings
    ) -> None:
        ragu_path = workspace / "recipes" / "ragu.md"
        content = ragu_path.read_text(encoding="utf-8")
        ragu_path.write_text(
            content.replace("target: soffritto", "target: ghost-doc"),
            encoding="utf-8",
        )

        report = run(settings)

        assert any(
            "invalid_promotion" in v
            for v in report.documents["ragu"].hard_violations
        )

    def test_does_not_flag_draft_with_violations(
        self, workspace: Path, settings: Settings
    ) -> None:
        # Add a dangling slug to the draft document.
        draft_path = workspace / "drafts" / "unfinished-idea.md"
        content = draft_path.read_text(encoding="utf-8")
        draft_path.write_text(
            content.replace(
                "tags: [fleeting]",
                "tags: [fleeting]\nrelations:\n  - target: ghost\n    type: inspired_by",
            ),
            encoding="utf-8",
        )

        report = run(settings)

        assert not any(
            "invalid_promotion" in v
            for v in report.documents["unfinished-idea"].hard_violations
        )


# ---------------------------------------------------------------------------
# Reciprocal auto-injection
# ---------------------------------------------------------------------------


class TestReciprocalInjection:
    """Auto-injection of missing reciprocal relations."""

    def test_injects_missing_superseded_by(
        self, workspace: Path, settings: Settings
    ) -> None:
        # Remove the auto_injected superseded_by from soffritto so the
        # linter has to inject it.
        soffritto_path = workspace / "recipes" / "soffritto.md"
        content = soffritto_path.read_text(encoding="utf-8")
        # Strip the existing injected relation entirely.
        lines = [
            line
            for line in content.splitlines(keepends=True)
            if "superseded_by" not in line
            and "auto_injected" not in line
            and "target: ragu" not in line
        ]
        soffritto_path.write_text("".join(lines), encoding="utf-8")

        # Add a supersedes relation to ragu.
        ragu_path = workspace / "recipes" / "ragu.md"
        ragu_content = ragu_path.read_text(encoding="utf-8")
        ragu_path.write_text(
            ragu_content.replace(
                "  - target: soffritto\n    type: derived_from",
                "  - target: soffritto\n    type: supersedes",
            ),
            encoding="utf-8",
        )

        report = run(settings)

        assert report.summary.injected >= 1
        assert any(
            "injected" in i for i in report.documents["soffritto"].injected
        )

    def test_does_not_reinject_existing_reciprocal(
        self, settings: Settings
    ) -> None:
        # The fixture workspace already has the auto_injected relation on
        # soffritto — the linter should not inject it again.
        report = run(settings)

        assert report.summary.injected == 0


# ---------------------------------------------------------------------------
# Soft warnings
# ---------------------------------------------------------------------------


class TestCompletenessWarnings:
    """Completeness soft warnings."""

    def test_warns_when_no_authored_relations(
        self, workspace: Path, settings: Settings
    ) -> None:
        # unfinished-idea has no relations — should trigger incomplete warning.
        report = run(settings)

        assert any(
            "incomplete" in w
            for w in report.documents["unfinished-idea"].warnings
        )

    def test_no_completeness_warning_when_relations_present(
        self, settings: Settings
    ) -> None:
        report = run(settings)

        # ragu has one authored relation.
        assert not any(
            "incomplete" in w and "relation" in w
            for w in report.documents["ragu"].warnings
        )


# ---------------------------------------------------------------------------
# Report structure
# ---------------------------------------------------------------------------


class TestLintReportStructure:
    """LintReport dataclass properties."""

    def test_document_report_clean_property(self) -> None:
        clean = DocumentReport(status="draft")
        dirty = DocumentReport(
            status="published",
            hard_violations=["dangling_slug: target 'x' does not exist"],
        )

        assert clean.clean is True
        assert dirty.clean is False

    def test_lint_report_clean_property(self, settings: Settings) -> None:
        report = run(settings)

        assert report.clean == (report.summary.hard_violations == 0)

    def test_generated_at_is_set(self, settings: Settings) -> None:
        report = run(settings)

        assert report.generated_at != ""


# ---------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------


class TestWrite:
    """Tests for `lint.write`."""

    def test_creates_keep_dir_if_missing(self, settings: Settings) -> None:
        assert not settings.keep_dir.exists()
        report = run(settings)
        write(report, settings)

        assert settings.keep_dir.exists()

    def test_writes_lint_json(self, settings: Settings) -> None:
        report = run(settings)
        output = write(report, settings)

        assert output.exists()
        assert output.name == "lint.json"

    def test_written_file_is_valid_json(self, settings: Settings) -> None:
        report = run(settings)
        output = write(report, settings)
        parsed = json.loads(output.read_text(encoding="utf-8"))

        assert "summary" in parsed
        assert "documents" in parsed
        assert "generated_at" in parsed

    def test_summary_fields_present(self, settings: Settings) -> None:
        report = run(settings)
        output = write(report, settings)
        parsed = json.loads(output.read_text(encoding="utf-8"))

        assert "total" in parsed["summary"]
        assert "hard_violations" in parsed["summary"]
        assert "warnings" in parsed["summary"]
        assert "injected" in parsed["summary"]

    def test_returns_path_to_written_file(self, settings: Settings) -> None:
        report = run(settings)
        output = write(report, settings)

        assert output == settings.keep_dir / "lint.json"
