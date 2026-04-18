"""Command-line interface for Keep.

Provides a single `keep` entrypoint with subcommands. The workspace root is
resolved implicitly from the current working directory — Keep looks for
`keep.yml` to confirm it is at the workspace root.

Usage::

    keep graph       # rebuild .keep/graph.json
    keep index       # rebuild index.md
    keep lint        # lint workspace documents
    keep state       # update .keep/state.json
"""

from __future__ import annotations

import sys
import argparse

from pathlib import Path

from keep import graph
from keep import index as index_module
from keep import lint as lint_module
from keep import state as state_module
from keep.logging import get_logger, set_verbosity
from keep.settings import CONFIG_FILENAME, Settings


log = get_logger(__name__)


def main() -> None:
    """Entrypoint for the `keep` CLI."""
    parser = argparse.ArgumentParser(
        prog="keep",
        description="Keep — personal wiki tooling.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable debug logging.",
    )
    subparsers = parser.add_subparsers(dest="command", metavar="command")
    subparsers.required = True

    # keep graph
    graph_parser = subparsers.add_parser(
        "graph",
        help="Rebuild .keep/graph.json from frontmatter.",
    )
    graph_parser.set_defaults(func=_cmd_graph)

    # keep index
    index_parser = subparsers.add_parser(
        "index",
        help="Rebuild index.md from frontmatter.",
    )
    index_parser.set_defaults(func=_cmd_index)

    # keep lint
    lint_parser = subparsers.add_parser(
        "lint",
        help="Lint workspace documents and write .keep/lint.json.",
    )
    lint_parser.set_defaults(func=_cmd_lint)

    # keep state
    state_parser = subparsers.add_parser(
        "state",
        help=(
            "Update .keep/state.json with latest document hashes and "
            "timestamps."
        ),
    )
    state_parser.set_defaults(func=_cmd_state)

    args = parser.parse_args()
    set_verbosity(args.verbose)

    workspace = _resolve_workspace()
    settings = Settings.load(workspace)
    args.func(args, settings)


def _cmd_graph(args: argparse.Namespace, settings: Settings) -> None:
    """Handle the `keep graph` subcommand.

    Args:
        args: Parsed CLI arguments. Reserved for future `keep graph` flags
            such as `--dry-run`; unused until then.
        settings: Resolved workspace settings.
    """
    _ = args
    g = graph.build(settings)
    output = graph.write(g, settings)

    node_count = len(g["nodes"])
    edge_count = len(g["edges"])
    print(
        f"graph written to {output.relative_to(settings.workspace)} "
        f"({node_count} node(s), {edge_count} edge(s))"
    )


def _cmd_index(args: argparse.Namespace, settings: Settings) -> None:
    """Handle the `keep index` subcommand.

    Args:
        args: Parsed CLI arguments. Reserved for future `keep index` flags;
            unused until then.
        settings: Resolved workspace settings.
    """
    _ = args
    rows = index_module.build(settings)
    output = index_module.write(rows, settings)

    print(
        f"index written to {output.relative_to(settings.workspace)} "
        f"({len(rows)} document(s))"
    )


def _cmd_lint(args: argparse.Namespace, settings: Settings) -> None:
    """Handle the `keep lint` subcommand.

    Prints a summary and per-document violations to stdout. Exits with code 1
    if any hard violations are found.

    Args:
        args: Parsed CLI arguments. Reserved for future `keep lint` flags;
            unused until then.
        settings: Resolved workspace settings.
    """
    _ = args
    report = lint_module.run(settings)
    output = lint_module.write(report, settings)

    _print_lint_report(report)
    print(f"\nreport written to {output.relative_to(settings.workspace)}")

    if not report.clean:
        sys.exit(1)


def _cmd_state(args: argparse.Namespace, settings: Settings) -> None:
    """Handle the `keep state` subcommand.

    Args:
        args: Parsed CLI arguments. Reserved for future `keep state` flags;
            unused until then.
        settings: Resolved workspace settings.
    """
    _ = args
    current = state_module.load(settings)
    updated = state_module.update(current, settings)
    output = state_module.write(updated, settings)

    doc_count = len(updated.documents)
    print(
        f"state written to {output.relative_to(settings.workspace)} "
        f"({doc_count} document(s))"
    )


def _print_lint_report(report: lint_module.LintReport) -> None:
    """Print a human-readable lint report to stdout.

    Args:
        report: Lint report to render.
    """
    s = report.summary
    status = "✓ clean" if report.clean else "✗ violations found"
    print(
        f"lint: {status} — "
        f"{s.total} document(s), "
        f"{s.hard_violations} hard violation(s), "
        f"{s.warnings} warning(s), "
        f"{s.injected} injected"
    )

    for slug, doc_report in sorted(report.documents.items()):
        if (
            not doc_report.hard_violations
            and not doc_report.warnings
            and not doc_report.injected
        ):
            continue

        print(f"\n  {slug} [{doc_report.status}]")

        for v in doc_report.hard_violations:
            print(f"    ✗ {v}")
        for w in doc_report.warnings:
            print(f"    ⚠ {w}")
        for i in doc_report.injected:
            print(f"    ↩ {i}")


def _resolve_workspace() -> Path:
    """Resolve the workspace root from the current working directory.

    Keep uses implicit root detection: the current directory must contain
    `keep.yml`. This mirrors the convention used by tools like git.

    Returns:
        Path to the workspace root.

    Raises:
        SystemExit: If `keep.yml` is not found in the current directory.
    """
    cwd = Path.cwd()
    if not (cwd / CONFIG_FILENAME).exists():
        print(
            f"error: {CONFIG_FILENAME} not found in {cwd}\n"
            "Make sure you are running 'keep' from your workspace root.",
            file=sys.stderr,
        )
        sys.exit(1)
    return cwd


if __name__ == "__main__":
    main()
