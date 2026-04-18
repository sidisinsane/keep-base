################################################################################
# tasks/docs.make (docs)
# Tasks for building and serving Sphinx documentation.
################################################################################
.PHONY: docs/build docs/clean docs/serve

docs-sphinx-deps:
	@which sphinx-build > /dev/null || (echo "Error: sphinx-build not found. Run: uv sync --dev"; exit 1)

docs-python-deps:
	@which python > /dev/null || (echo "Error: python not found"; exit 1)

## Build HTML documentation with Sphinx.
docs/build: docs-sphinx-deps
	@echo "Building documentation..."
	@uv run sphinx-build -b html docs docs/_build/html
	@echo "Documentation built at docs/_build/html/index.html"

## Remove the Sphinx build output and generated stubs.
docs/clean:
	@echo "Cleaning documentation build..."
	@rm -rf docs/_build docs/generated
	@echo "Done."

## Serve the built documentation locally on http://localhost:8000.
docs/serve: docs-python-deps
	@echo "Serving documentation at http://localhost:8000 (Ctrl+C to stop)..."
	@python -m http.server 8000 --directory docs/_build/html
