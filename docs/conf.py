"""Sphinx configuration for Keep."""

from __future__ import annotations

import sys
from pathlib import Path

from sphinx_pyproject import SphinxConfig


# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------

# Ensure the src/ layout is on the path so autodoc can import keep modules.
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# ---------------------------------------------------------------------------
# Project metadata — read from pyproject.toml via sphinx-pyproject
# ---------------------------------------------------------------------------

config = SphinxConfig("../pyproject.toml", globalns=globals())

# ---------------------------------------------------------------------------
# General configuration
# ---------------------------------------------------------------------------

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinx.ext.githubpages",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# ---------------------------------------------------------------------------
# Autodoc
# ---------------------------------------------------------------------------

# Mock ruamel.yaml so autodoc can import keep modules without the runtime
# dependency installed in the docs build environment.
autodoc_mock_imports = ["ruamel"]

# Show type hints in the description, not the signature.
autodoc_typehints = "description"

# ---------------------------------------------------------------------------
# Autosummary
# ---------------------------------------------------------------------------

# Generate stub .rst files automatically during sphinx-build.
# The generated/ directory is excluded from version control.
autosummary_generate = True
autosummary_imported_members = False

# ---------------------------------------------------------------------------
# Napoleon (Google-style docstrings)
# ---------------------------------------------------------------------------

napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = False
napoleon_use_param = True
napoleon_use_rtype = True

# ---------------------------------------------------------------------------
# Intersphinx — link to Python stdlib docs
# ---------------------------------------------------------------------------

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}

# ---------------------------------------------------------------------------
# HTML output — Furo theme
# ---------------------------------------------------------------------------

html_theme = "furo"
html_static_path = []

html_theme_options = {
    "sidebar_hide_name": False,
    "navigation_with_keys": True,
}

# Disable the "View page source" button — it exposes raw RST, which is not
# useful for end users. Per-object [source] links are provided by viewcode.
html_show_sourcelink = False
