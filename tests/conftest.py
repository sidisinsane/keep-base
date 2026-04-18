"""Shared pytest fixtures for Keep tests.

Fixtures are organised by scope:
- `fixture_dir`: session-scoped path to the fixtures directory.
- `workspace_dir`: session-scoped path to the valid test workspace.
- `invalid_dir`: session-scoped path to the invalid fixture documents.
- `workspace`: function-scoped copy of the test workspace under `tmp_path`,
  so each test gets an isolated, writable workspace.
- `settings`: function-scoped `Settings` instance for the copied workspace.
"""

from __future__ import annotations

import shutil

from pathlib import Path

import pytest

from keep.settings import Settings


# Absolute path to the fixtures directory, resolved relative to this file.
_FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def fixture_dir() -> Path:
    """Return the absolute path to the top-level fixtures directory.

    Returns:
        Path to `tests/fixtures/`.
    """
    return _FIXTURES_DIR


@pytest.fixture(scope="session")
def workspace_dir() -> Path:
    """Return the absolute path to the valid test workspace fixture.

    Returns:
        Path to `tests/fixtures/workspace/`.
    """
    return _FIXTURES_DIR / "workspace"


@pytest.fixture(scope="session")
def invalid_dir() -> Path:
    """Return the absolute path to the invalid fixture documents.

    Returns:
        Path to `tests/fixtures/invalid/`.
    """
    return _FIXTURES_DIR / "invalid"


@pytest.fixture()
def workspace(tmp_path: Path, workspace_dir: Path) -> Path:
    """Copy the test workspace into a temporary directory.

    Each test receives a fresh, isolated, writable copy of the workspace.
    This prevents tests from polluting shared fixture state when they write
    derived artefacts like `.keep/graph.json`.

    The `.keep/` directory is explicitly removed after copying to guarantee
    a clean state, even if a previous test run left artefacts in the fixture
    source directory.

    Args:
        tmp_path: Pytest-provided temporary directory, unique per test.
        workspace_dir: Session-scoped path to the source workspace fixture.

    Returns:
        Path to the copied workspace root inside `tmp_path`.
    """
    dest = tmp_path / "workspace"
    shutil.copytree(workspace_dir, dest)

    keep_dir = dest / ".keep"
    if keep_dir.exists():
        shutil.rmtree(keep_dir)

    return dest


@pytest.fixture()
def settings(workspace: Path) -> Settings:
    """Return a `Settings` instance loaded from the temporary workspace.

    Args:
        workspace: Function-scoped temporary workspace path.

    Returns:
        Populated `Settings` instance.
    """
    return Settings.load(workspace)
