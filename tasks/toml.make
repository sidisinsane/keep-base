################################################################################
# tasks/toml.make (toml)
# Tasks related to toml.
################################################################################
.PHONY: toml/fmt toml/pyproject-fmt toml/tidy

toml-dprint-deps:
	@which dprint > /dev/null || (echo "Error: dprint not found"; exit 1)

toml-pyproject-fmt-deps:
	@which pyproject-fmt > /dev/null || (echo "Error: pyproject-fmt not found"; exit 1)


## Format all toml files with dprint.
toml/fmt: toml-dprint-deps
	@echo "Formatting all toml files..."
	@dprint fmt --config dprint.json "**/*.{toml}"

## Format pyproject.toml.
toml/pyproject-fmt: toml-pyproject-fmt-deps
	@echo "Formatting pyproject.toml..."
	@uv run pyproject-fmt --config pyproject-fmt.toml pyproject.toml > logs/pyproject-fmt.diff

## Tidy all toml files.
toml/tidy: toml/pyproject-fmt toml/fmt
	@echo "Tidied all toml files."