################################################################################
# tasks/py.make (py)
# Tasks for Python linting, formatting, security analysis, and testing.
################################################################################
.PHONY: py/lint py/fix py/fmt py/tidy py/security py/test py/test-v py/test-x

py-ruff-deps:
	@which ruff > /dev/null || (echo "Error: ruff not found. Run: uv sync --dev"; exit 1)

py-bandit-deps:
	@which bandit > /dev/null || (echo "Error: bandit not found. Run: uv sync --dev"; exit 1)

py-pytest-deps:
	@which pytest > /dev/null || (echo "Error: pytest not found. Run: uv sync --dev"; exit 1)


## Lint all python files.
py/lint: py-ruff-deps
	@echo "Checking formatting of all python files..."
	@uv run ruff format src/ --check
	@echo "Linting all python files..."
	@uv run ruff check src/ > logs/ruff.json

## Format all python files.
py/fmt: py-ruff-deps
	@echo "Formatting all python files..."
	@uv run ruff format src/

## Fix all python files.
py/fix: py-ruff-deps
	@echo "Fixing all python files..."
	@uv run ruff check src/ --fix > logs/ruff.json

## Tidy all python files.
py/tidy: py/fmt py/fix
	@echo "Tidied all python files..."

## Run security analysis with bandit.
py/security: py-bandit-deps
	@echo "Running security analysis..."
	@uv run bandit -c pyproject.toml -r src/keep/ --severity-level medium --confidence-level low

## Run tests with coverage.
py/test: py-pytest-deps
	@echo "Running tests..."
	@uv run pytest

## Run tests with verbose output.
py/test-v: py-pytest-deps
	@echo "Running tests (verbose)..."
	@uv run pytest -v

## Run tests, stop on first failure.
py/test-x: py-pytest-deps
	@echo "Running tests (fail fast)..."
	@uv run pytest -x
