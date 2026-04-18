################################################################################
# tasks/md.make (md)
# Tasks related to markdown.
################################################################################
.PHONY: md/fix md/wrap md/lint md/tidy

md-dprint-deps:
	@which dprint > /dev/null || (echo "Error: dprint not found"; exit 1)

md-rumdl-deps:
	@which rumdl > /dev/null || (echo "Error: rumdl not found. Run: uv sync --dev"; exit 1)


## Fixing all markdown files.
md/fix: md-rumdl-deps
	@echo "Fixing all markdown files..."
	@uv run rumdl check --fix . > logs/rumdl.jsonl

## Wrap text in all markdown files.
md/wrap: md-dprint-deps
	@echo "Wrapping text in all markdown files..."
	@uv run dprint fmt "**/*.{md,mdown,markdown}"

## Lint all markdown files.
md/lint: md-rumdl-deps
	@echo "Linting all markdown files..."
	@uv run rumdl check . > logs/rumdl.jsonl

## Tidy all markdown files.
md/tidy: md/fix md/wrap md/lint
	@echo "Tidied all markdown files."