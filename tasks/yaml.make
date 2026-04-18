################################################################################
# tasks/yaml.make (yaml)
# Tasks related to yaml.
################################################################################
.PHONY: yaml/fix yaml/fix-qm yaml/lint yaml/tidy

yaml-dprint-deps:
	@which dprint > /dev/null || (echo "Error: dprint not found"; exit 1)

yaml-yamlfix-deps:
	@which yamlfix > /dev/null || (echo "Error: yamlfix not found"; exit 1)

yaml-yamllint-deps:
	@which yamllint > /dev/null || (echo "Error: yamllint not found"; exit 1)

## Fix all yaml files.
yaml/fix: yaml-yamlfix-deps
	@echo "Fixing all yaml files..."
	@uv run yamlfix --exclude ".github/**/*" --exclude ".venv/**/*"  .

## Fix quotation-marks in all yaml files (yamlfix fix).
yaml/fix-qm: yaml-dprint-deps
	@echo "Fixing quotation-marks in all yaml files..."
	@uv run dprint fmt "**/*.{yml,yaml}"

## Lint all yaml files.
yaml/lint: yaml-yamllint-deps
	@echo "Linting all yaml files..."
	@uv run yamllint .

## Tidy all yaml files.
yaml/tidy: yaml/fix yaml/fix-qm yaml/lint
	@echo "Tidied all yaml files."