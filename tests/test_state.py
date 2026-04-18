"""Tests for `keep.state`."""

from __future__ import annotations

import json
from pathlib import Path

from keep.settings import Settings
from keep.state import (
    DocumentState,
    State,
    STATE_SCHEMA_VERSION,
    load,
    update,
    write,
)


class TestLoad:
    """Tests for `state.load`."""

    def test_returns_empty_state_when_file_missing(
        self, settings: Settings
    ) -> None:
        result = load(settings)

        assert isinstance(result, State)
        assert result.documents == {}

    def test_returns_empty_state_on_corrupt_file(
        self, settings: Settings
    ) -> None:
        settings.keep_dir.mkdir(exist_ok=True)
        settings.state_path.write_text("not valid json", encoding="utf-8")

        result = load(settings)

        assert result.documents == {}

    def test_loads_existing_state(self, settings: Settings) -> None:
        settings.keep_dir.mkdir(exist_ok=True)
        settings.state_path.write_text(
            json.dumps({
                "schema_version": 1,
                "generated_at": "2026-01-01T00:00:00+00:00",
                "documents": {
                    "ragu": {
                        "last_meaningful_modification": "2026-01-01T00:00:00+00:00",
                        "content_hash": "a3f1c9d2",
                        "meaningful_hash": "7b2e40a1",
                        "status_at_last_check": "published",
                    }
                },
            }),
            encoding="utf-8",
        )

        result = load(settings)

        assert "ragu" in result.documents
        assert result.documents["ragu"].content_hash == "a3f1c9d2"
        assert result.documents["ragu"].status_at_last_check == "published"

    def test_loaded_state_has_correct_schema_version(
        self, settings: Settings
    ) -> None:
        settings.keep_dir.mkdir(exist_ok=True)
        settings.state_path.write_text(
            json.dumps({"schema_version": 1, "generated_at": "", "documents": {}}),
            encoding="utf-8",
        )

        result = load(settings)

        assert result.schema_version == 1


class TestUpdate:
    """Tests for `state.update`."""

    def test_seeds_new_documents(self, settings: Settings) -> None:
        empty = State()
        result = update(empty, settings)

        # workspace has: ragu, soffritto, marcella-hazan, unfinished-idea
        assert len(result.documents) == 4

    def test_new_document_has_all_required_fields(
        self, settings: Settings
    ) -> None:
        result = update(State(), settings)
        doc = result.documents["ragu"]

        assert doc.last_meaningful_modification
        assert doc.content_hash
        assert doc.meaningful_hash
        assert doc.status_at_last_check == "published"

    def test_unchanged_document_preserves_timestamp(
        self, settings: Settings
    ) -> None:
        first = update(State(), settings)
        original_ts = first.documents["ragu"].last_meaningful_modification

        second = update(first, settings)

        assert second.documents["ragu"].last_meaningful_modification == original_ts

    def test_cosmetic_change_preserves_timestamp(
        self, workspace: Path, settings: Settings
    ) -> None:
        first = update(State(), settings)
        original_ts = first.documents["ragu"].last_meaningful_modification

        # Modify only the summary (cosmetic — not in meaningful fields).
        ragu_path = workspace / "recipes" / "ragu.md"
        content = ragu_path.read_text(encoding="utf-8")
        ragu_path.write_text(
            content.replace(
                "Classic slow-cooked Bolognese built on a soffritto base.",
                "Updated summary that is purely cosmetic.",
            ),
            encoding="utf-8",
        )

        second = update(first, settings)

        assert second.documents["ragu"].last_meaningful_modification == original_ts

    def test_cosmetic_change_updates_content_hash(
        self, workspace: Path, settings: Settings
    ) -> None:
        first = update(State(), settings)
        original_c_hash = first.documents["ragu"].content_hash

        ragu_path = workspace / "recipes" / "ragu.md"
        content = ragu_path.read_text(encoding="utf-8")
        ragu_path.write_text(
            content.replace(
                "Classic slow-cooked Bolognese built on a soffritto base.",
                "Updated summary that is purely cosmetic.",
            ),
            encoding="utf-8",
        )

        second = update(first, settings)

        assert second.documents["ragu"].content_hash != original_c_hash

    def test_meaningful_change_resets_timestamp(
        self, workspace: Path, settings: Settings
    ) -> None:
        first = update(State(), settings)
        original_ts = first.documents["ragu"].last_meaningful_modification

        # Change status — a meaningful field.
        ragu_path = workspace / "recipes" / "ragu.md"
        content = ragu_path.read_text(encoding="utf-8")
        ragu_path.write_text(
            content.replace("status: published", "status: review"),
            encoding="utf-8",
        )

        second = update(first, settings)

        assert second.documents["ragu"].last_meaningful_modification != original_ts

    def test_meaningful_change_updates_status_at_last_check(
        self, workspace: Path, settings: Settings
    ) -> None:
        first = update(State(), settings)

        ragu_path = workspace / "recipes" / "ragu.md"
        content = ragu_path.read_text(encoding="utf-8")
        ragu_path.write_text(
            content.replace("status: published", "status: review"),
            encoding="utf-8",
        )

        second = update(first, settings)

        assert second.documents["ragu"].status_at_last_check == "review"

    def test_skips_files_inside_keep_dir(
        self, workspace: Path, settings: Settings
    ) -> None:
        keep_dir = workspace / ".keep"
        keep_dir.mkdir(exist_ok=True)
        stray = keep_dir / "stray.md"
        stray.write_text(
            "---\n"
            "slug: stray\n"
            "title: Stray\n"
            "kind: note\n"
            "status: draft\n"
            "date_created: '2026-01-01'\n"
            "tags: []\n"
            "---\n",
            encoding="utf-8",
        )

        result = update(State(), settings)

        assert "stray" not in result.documents

    def test_skips_malformed_documents_without_aborting(
        self, workspace: Path, settings: Settings
    ) -> None:
        bad = workspace / "bad.md"
        bad.write_text("# No frontmatter here\n", encoding="utf-8")

        result = update(State(), settings)

        assert len(result.documents) == 4

    def test_generated_at_is_set(self, settings: Settings) -> None:
        result = update(State(), settings)

        assert result.generated_at != ""

    def test_schema_version_is_set(self, settings: Settings) -> None:
        result = update(State(), settings)

        assert result.schema_version == STATE_SCHEMA_VERSION


class TestWrite:
    """Tests for `state.write`."""

    def test_creates_keep_dir_if_missing(self, settings: Settings) -> None:
        assert not settings.keep_dir.exists()
        s = update(State(), settings)
        write(s, settings)

        assert settings.keep_dir.exists()

    def test_writes_state_json(self, settings: Settings) -> None:
        s = update(State(), settings)
        output = write(s, settings)

        assert output.exists()
        assert output.suffix == ".json"

    def test_written_file_is_valid_json(self, settings: Settings) -> None:
        s = update(State(), settings)
        output = write(s, settings)
        parsed = json.loads(output.read_text(encoding="utf-8"))

        assert "schema_version" in parsed
        assert "documents" in parsed

    def test_returns_path_to_written_file(self, settings: Settings) -> None:
        s = update(State(), settings)
        output = write(s, settings)

        assert output == settings.state_path

    def test_written_state_can_be_reloaded(self, settings: Settings) -> None:
        s = update(State(), settings)
        write(s, settings)

        reloaded = load(settings)

        assert set(reloaded.documents.keys()) == set(s.documents.keys())

    def test_round_trip_preserves_timestamps(self, settings: Settings) -> None:
        s = update(State(), settings)
        write(s, settings)
        reloaded = load(settings)

        for slug, doc in s.documents.items():
            assert (
                reloaded.documents[slug].last_meaningful_modification
                == doc.last_meaningful_modification
            )
