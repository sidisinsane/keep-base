# pylint: disable=unnecessary-comprehension,broad-exception-caught
"""Linter for Keep workspace documents.

Validates all documents in a workspace, checks for hard violations that block
graduation, emits soft warnings for completeness and staleness, and
auto-injects missing reciprocal relations.

The linter produces a structured :class:`LintReport` which is both persisted
as `.keep/lint.json` and rendered for the terminal by the CLI.

Hard violations (block graduation to ``published`` or ``canon``):

- ``dangling_slug``: a relation target does not resolve to a known slug.
- ``private_target_in_public_doc``: a non-private document relates to a
  private one.
- ``missing_reciprocal``: a ``contradicts`` or ``supersedes`` relation exists
  without the corresponding backlink (should only occur if auto-injection
  failed).
- ``invalid_promotion``: a document is ``published`` or ``canon`` but has
  outstanding hard violations.

Soft warnings (advisory, do not block graduation):

- ``incomplete``: completeness ratio is below the configured threshold.
- ``stale``: document has not had a meaningful modification within the
  threshold for its status.

Typical usage::

    from keep.lint import run

    settings = Settings.load(workspace)
    report = run(settings)
"""

from __future__ import annotations

import io
import json

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

from keep.logging import get_logger
from keep.settings import Settings
from keep.state import State
from keep.state import load as load_state
from keep.utils.frontmatter import Frontmatter, FrontmatterError, parse


log = get_logger(__name__)

_yaml = YAML()
_yaml.preserve_quotes = True

#: Statuses that require a clean lint pass before promotion.
_GATED_STATUSES = frozenset({"published", "canon"})

#: Frontmatter delimiter.
_FM_DELIMITER = "---"


@dataclass
class DocumentReport:
    """Lint results for a single document.

    Attributes:
        status: The document's current lifecycle status.
        hard_violations: List of hard violation messages. Any entry here
            blocks graduation to `published` or `canon`.
        warnings: List of soft warning messages. Advisory only.
        injected: List of descriptions of reciprocal relations that were
            auto-injected into this document's frontmatter.
    """

    status: str
    hard_violations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    injected: list[str] = field(default_factory=list)

    @property
    def clean(self) -> bool:
        """Return True if the document has no hard violations."""
        return len(self.hard_violations) == 0


@dataclass
class LintSummary:
    """Aggregate counts across the full lint run.

    Attributes:
        total: Total number of documents linted.
        hard_violations: Total number of hard violations across all documents.
        warnings: Total number of soft warnings across all documents.
        injected: Total number of reciprocal relations auto-injected.
    """

    total: int = 0
    hard_violations: int = 0
    warnings: int = 0
    injected: int = 0


@dataclass
class LintReport:
    """Full lint report for a workspace.

    Attributes:
        generated_at: ISO 8601 timestamp of the lint run.
        summary: Aggregate counts.
        documents: Per-document results, keyed by slug.
    """

    generated_at: str
    summary: LintSummary
    documents: dict[str, DocumentReport]

    @property
    def clean(self) -> bool:
        """Return True if no documents have hard violations."""
        return self.summary.hard_violations == 0


def run(settings: Settings) -> LintReport:
    """Run the full lint pass against a workspace.

    Steps performed:
    1. Parse all documents and build a slug index.
    2. Auto-inject missing reciprocal relations where needed.
    3. Re-parse any modified documents.
    4. Check hard violations for each document.
    5. Check soft warnings (completeness, staleness).
    6. Flag invalid promotions for gated statuses with violations.

    Args:
        settings: Resolved workspace settings.

    Returns:
        Populated :class:`LintReport`.
    """
    state = load_state(settings)
    docs = _parse_all(settings)
    slug_index = {slug: doc for slug, doc in docs.items()}
    private_slugs = {slug for slug, doc in docs.items() if doc.private}

    doc_reports: dict[str, DocumentReport] = {}

    # Auto-inject reciprocals before checking violations so the missing
    # reciprocal check reflects the post-injection state.
    injections = _inject_reciprocals(docs, slug_index, settings)

    # Re-parse documents that were modified by injection.
    for slug in injections:
        if slug in docs:
            path = docs[slug].source_path
            try:
                docs[slug] = parse(path)
            except FrontmatterError as exc:
                log.warning(
                    "could not re-parse %s after injection: %s", slug, exc
                )

    for slug, doc in sorted(docs.items()):
        report = DocumentReport(status=doc.status)

        _check_hard_violations(doc, slug_index, private_slugs, report)
        _check_warnings(doc, state, settings, report)

        if doc.status in _GATED_STATUSES and not report.clean:
            report.hard_violations.append(
                f"invalid_promotion: '{doc.status}' requires zero hard "
                f"violations but {len(report.hard_violations)} found"
            )

        report.injected = injections.get(slug, [])
        doc_reports[slug] = report

    summary = LintSummary(
        total=len(doc_reports),
        hard_violations=sum(
            len(r.hard_violations) for r in doc_reports.values()
        ),
        warnings=sum(len(r.warnings) for r in doc_reports.values()),
        injected=sum(len(r.injected) for r in doc_reports.values()),
    )

    return LintReport(
        generated_at=datetime.now(timezone.utc).isoformat(),
        summary=summary,
        documents=doc_reports,
    )


def write(report: LintReport, settings: Settings) -> Path:
    """Write the lint report to `.keep/lint.json`.

    Creates the `.keep/` directory if it does not exist.

    Args:
        report: Lint report as returned by :func:`run`.
        settings: Resolved workspace settings.

    Returns:
        Path to the written file.
    """
    settings.keep_dir.mkdir(exist_ok=True)
    output = settings.keep_dir / "lint.json"
    output.write_text(
        json.dumps(_serialise(report), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return output


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _parse_all(settings: Settings) -> dict[str, Frontmatter]:
    """Parse all workspace documents into a slug-keyed dictionary.

    Args:
        settings: Resolved workspace settings.

    Returns:
        Mapping of slug to parsed :class:`Frontmatter`.
    """
    keep_dir_name = settings.keep_dir.name
    docs: dict[str, Frontmatter] = {}

    for path in sorted(settings.workspace.rglob("*.md")):
        if keep_dir_name in path.relative_to(settings.workspace).parts:
            continue
        if path == settings.index_path:
            continue
        try:
            doc = parse(path)
            docs[doc.slug] = doc
        except FrontmatterError as exc:
            log.warning(
                "skipping %s: %s",
                path.relative_to(settings.workspace),
                exc,
            )

    return docs


def _inject_reciprocals(
    docs: dict[str, Frontmatter],
    slug_index: dict[str, Frontmatter],
    settings: Settings,
) -> dict[str, list[str]]:
    """Auto-inject missing reciprocal relations for symmetric relation types.

    For each `contradicts` or `supersedes` relation in document A pointing to
    document B, if B does not already have the corresponding reciprocal, it is
    written into B's frontmatter file.

    Args:
        docs: All parsed documents keyed by slug.
        slug_index: Same mapping, used for target lookups.
        settings: Resolved workspace settings.

    Returns:
        Mapping of slug to list of injection description strings, for
        documents that had relations injected.
    """
    symmetry = settings.schema.get("relation_symmetry", {})
    injected: dict[str, list[str]] = {}

    for slug, doc in docs.items():
        for relation in doc.relations:
            sym = symmetry.get(relation.type, {})
            if not sym.get("symmetric"):
                continue

            target_slug = relation.target
            target_doc = slug_index.get(target_slug)
            if target_doc is None:
                continue

            reciprocal_type = sym.get("reciprocal_type", relation.type)

            # Check if reciprocal already exists.
            already_present = any(
                r.target == slug and r.type == reciprocal_type
                for r in target_doc.relations
            )
            if already_present:
                continue

            # Inject the reciprocal into the target document's file.
            success = _write_reciprocal(
                target_doc.source_path,
                source_slug=slug,
                reciprocal_type=reciprocal_type,
            )
            if success:
                injected.setdefault(target_slug, []).append(
                    f"injected '{reciprocal_type}' from '{slug}'"
                )
                log.debug(
                    "injected '%s' relation into %s from %s",
                    reciprocal_type,
                    target_slug,
                    slug,
                )

    return injected


def _write_reciprocal(
    path: Path,
    source_slug: str,
    reciprocal_type: str,
) -> bool:
    """Append a reciprocal relation to a document's frontmatter.

    Uses `ruamel.yaml` to parse and rewrite the frontmatter block, preserving
    all existing formatting and comments.

    Args:
        path: Path to the target Markdown file.
        source_slug: Slug of the document that initiated the relation.
        reciprocal_type: Relation type to inject.

    Returns:
        True if the injection succeeded, False otherwise.
    """
    try:
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines(keepends=True)

        # Find the frontmatter block boundaries.
        if not lines or lines[0].strip() != _FM_DELIMITER:
            return False

        closing = next(
            (
                i
                for i, line in enumerate(lines[1:], start=1)
                if line.strip() == _FM_DELIMITER
            ),
            None,
        )
        if closing is None:
            return False

        fm_text = "".join(lines[1:closing])
        data = _yaml.load(fm_text)

        if data is None:
            return False

        if "relations" not in data or data["relations"] is None:
            data["relations"] = []

        data["relations"].append(
            {
                "target": source_slug,
                "type": reciprocal_type,
                "auto_injected": True,
            }
        )

        stream = io.StringIO()
        _yaml.dump(data, stream)
        new_fm = stream.getvalue()

        new_lines = lines[0:1] + [new_fm] + lines[closing:]
        path.write_text("".join(new_lines), encoding="utf-8")
        return True

    except Exception as exc:
        log.warning("failed to inject reciprocal into %s: %s", path, exc)
        return False


def _check_hard_violations(
    doc: Frontmatter,
    slug_index: dict[str, Frontmatter],
    private_slugs: set[str],
    report: DocumentReport,
) -> None:
    """Populate `report.hard_violations` for a document.

    Args:
        doc: Parsed frontmatter.
        slug_index: All known slugs in the workspace.
        private_slugs: Set of slugs belonging to private documents.
        report: Report to populate in place.
    """
    for relation in doc.relations:
        target = relation.target

        # Dangling slug.
        if target not in slug_index:
            report.hard_violations.append(
                f"dangling_slug: target '{target}' does not exist"
            )
            continue

        # Private target in public document.
        if not doc.private and target in private_slugs:
            report.hard_violations.append(
                f"private_target_in_public_doc: '{target}' is private"
            )

        # Missing reciprocal — should be rare after auto-injection.
        sym_type = relation.type
        if sym_type in ("contradicts", "supersedes"):
            reciprocal_type = (
                "contradicts" if sym_type == "contradicts" else "superseded_by"
            )
            target_doc = slug_index[target]
            has_reciprocal = any(
                r.target == doc.slug and r.type == reciprocal_type
                for r in target_doc.relations
            )
            if not has_reciprocal:
                report.hard_violations.append(
                    f"missing_reciprocal: '{target}' has no "
                    f"'{reciprocal_type}' "
                    f"back to '{doc.slug}'"
                )


def _check_warnings(
    doc: Frontmatter,
    state: State,
    settings: Settings,
    report: DocumentReport,
) -> None:
    """Populate `report.warnings` for a document.

    Args:
        doc: Parsed frontmatter.
        state: Current state store.
        settings: Resolved workspace settings.
        report: Report to populate in place.
    """
    _check_completeness(doc, settings, report)
    _check_staleness(doc, state, settings, report)


def _check_completeness(
    doc: Frontmatter,
    settings: Settings,
    report: DocumentReport,
) -> None:
    """Flag documents whose completeness ratio is below the threshold.

    Args:
        doc: Parsed frontmatter.
        settings: Resolved workspace settings.
        report: Report to populate in place.
    """
    cfg = settings.completeness
    required = list(cfg.required_fields)

    # Check required fields presence.
    missing_fields = [f for f in required if not getattr(doc, f, None)]
    if missing_fields:
        report.warnings.append(
            f"incomplete: missing recommended field(s): "
            f"{', '.join(missing_fields)}"
        )

    # Check minimum relations count.
    authored_relations = [r for r in doc.relations if not r.auto_injected]
    if len(authored_relations) < cfg.required_relations:
        report.warnings.append(
            f"incomplete: has {len(authored_relations)} authored relation(s), "
            f"minimum is {cfg.required_relations}"
        )


def _check_staleness(
    doc: Frontmatter,
    state: State,
    settings: Settings,
    report: DocumentReport,
) -> None:
    """Flag docs that have not been meaningfully modified within the threshold.

    Staleness is skipped if state.json is empty (no prior run) or if the
    document has no state record yet.

    Args:
        doc: Parsed frontmatter.
        state: Current state store.
        settings: Resolved workspace settings.
        report: Report to populate in place.
    """
    doc_state = state.documents.get(doc.slug)
    if doc_state is None:
        return

    threshold_days = getattr(settings.staleness, doc.status, None)
    if threshold_days is None:
        return

    last_modified = datetime.fromisoformat(
        doc_state.last_meaningful_modification
    )
    age = datetime.now(timezone.utc) - last_modified
    age_days = age.days

    if age_days > threshold_days:
        report.warnings.append(
            f"stale: {age_days} day(s) since last meaningful modification "
            f"(threshold: {threshold_days})"
        )


def _serialise(report: LintReport) -> dict[str, Any]:
    """Convert a :class:`LintReport` to a JSON-serialisable dictionary.

    Args:
        report: Lint report to serialise.

    Returns:
        Plain dictionary ready for ``json.dumps``.
    """
    return {
        "generated_at": report.generated_at,
        "summary": {
            "total": report.summary.total,
            "hard_violations": report.summary.hard_violations,
            "warnings": report.summary.warnings,
            "injected": report.summary.injected,
        },
        "documents": {
            slug: {
                "status": doc_report.status,
                "hard_violations": doc_report.hard_violations,
                "warnings": doc_report.warnings,
                "injected": doc_report.injected,
            }
            for slug, doc_report in report.documents.items()
        },
    }
