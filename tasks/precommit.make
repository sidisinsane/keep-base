################################################################################
# tasks/precommit.make (precommit)
# Tasks for managing pre-commit hooks.
################################################################################
.PHONY: precommit/install precommit/run precommit/update precommit/clean

precommit-deps:
	@which pre-commit > /dev/null || (echo "Error: pre-commit not found. Run: uv sync --dev"; exit 1)

## Install pre-commit hooks into the local git repository.
precommit/install: precommit-deps
	@echo "Installing pre-commit hooks..."
	@uv run pre-commit install
	@echo "Done."

## Run all pre-commit hooks against all files.
precommit/run: precommit-deps
	@echo "Running pre-commit hooks on all files..."
	@uv run pre-commit run --all-files

## Update all pre-commit hook revisions to latest.
precommit/update: precommit-deps
	@echo "Updating pre-commit hooks..."
	@uv run pre-commit autoupdate
	@echo "Done."

## Remove pre-commit hook environments and uninstall from git.
precommit/clean: precommit-deps
	@echo "Cleaning pre-commit environments..."
	@uv run pre-commit clean
	@uv run pre-commit uninstall
	@echo "Done."
