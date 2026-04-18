"""Tests for `keep.graph`."""

from __future__ import annotations

import json

from datetime import datetime
from pathlib import Path

from keep.graph import build, write
from keep.settings import Settings


class TestBuild:
    """Tests for `graph.build`."""

    def test_returns_required_keys(self, settings: Settings) -> None:
        g = build(settings)

        assert "generated_at" in g
        assert "nodes" in g
        assert "edges" in g

    def test_node_count_matches_documents(self, settings: Settings) -> None:
        g = build(settings)

        # workspace_dir has: ragu, soffritto, marcella-hazan, unfinished-idea
        assert len(g["nodes"]) == 4

    def test_node_has_required_fields(self, settings: Settings) -> None:
        g = build(settings)
        node = next(n for n in g["nodes"] if n["slug"] == "ragu")

        assert node["slug"] == "ragu"
        assert node["title"] == "Ragù alla Bolognese"
        assert node["kind"] == "recipe"
        assert node["status"] == "published"
        assert node["private"] is False

    def test_edges_are_built_from_relations(self, settings: Settings) -> None:
        g = build(settings)
        edge = next(
            e
            for e in g["edges"]
            if e["from"] == "ragu" and e["to"] == "soffritto"
        )

        assert edge["type"] == "derived_from"
        assert edge["auto_injected"] is False

    def test_auto_injected_edge_preserved(self, settings: Settings) -> None:
        g = build(settings)
        edge = next(
            e
            for e in g["edges"]
            if e["from"] == "soffritto" and e["to"] == "ragu"
        )

        assert edge["auto_injected"] is True

    def test_document_with_no_relations_produces_no_edges(
        self, settings: Settings
    ) -> None:
        g = build(settings)
        edges_from_draft = [
            e for e in g["edges"] if e["from"] == "unfinished-idea"
        ]

        assert edges_from_draft == []

    def test_skips_keep_dir_markdown_files(
        self, workspace: Path, settings: Settings
    ) -> None:
        # Place a stray .md file inside .keep/ to confirm it is ignored.
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
            "---\n"
        )

        g = build(settings)
        slugs = [n["slug"] for n in g["nodes"]]

        assert "stray" not in slugs

    def test_skips_malformed_documents_without_aborting(
        self, workspace: Path, settings: Settings
    ) -> None:
        bad = workspace / "bad.md"
        bad.write_text("# No frontmatter here\n")

        g = build(settings)

        # Should still return the four valid documents.
        assert len(g["nodes"]) == 4

    def test_generated_at_is_iso_format(self, settings: Settings) -> None:
        g = build(settings)
        # Should parse without raising.
        datetime.fromisoformat(g["generated_at"])


class TestWrite:
    """Tests for `graph.write`."""

    def test_creates_keep_dir_if_missing(self, settings: Settings) -> None:
        assert not settings.keep_dir.exists()
        g = build(settings)
        write(g, settings)

        assert settings.keep_dir.exists()

    def test_writes_graph_json(self, settings: Settings) -> None:
        g = build(settings)
        output = write(g, settings)

        assert output.exists()
        assert output.suffix == ".json"

    def test_written_file_is_valid_json(self, settings: Settings) -> None:
        g = build(settings)
        output = write(g, settings)
        content = json.loads(output.read_text(encoding="utf-8"))

        assert "nodes" in content
        assert "edges" in content

    def test_returns_path_to_written_file(self, settings: Settings) -> None:
        g = build(settings)
        output = write(g, settings)

        assert output == settings.graph_path

    def test_overwrites_existing_graph(self, settings: Settings) -> None:
        settings.keep_dir.mkdir(exist_ok=True)
        settings.graph_path.write_text('{"stale": true}', encoding="utf-8")

        g = build(settings)
        write(g, settings)

        content = json.loads(settings.graph_path.read_text(encoding="utf-8"))
        assert "stale" not in content
