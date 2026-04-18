################################################################################
# tasks/gen.make (gen)
# Generating tasks.
################################################################################
.PHONY: gen/gitignore gen/tree

GEN_PROJECT_NAME := $(notdir $(CURDIR))

# List your project-specific ignores here (space-separated)
# You can use the backslash \ to keep it vertical and readable
GEN_GITIGNORE_EXTRAS := \
	.rumdl_cache/ \
	.yamlfix_cache/ \
	__IGNORE__/ \
	docs/_build/ \
	docs/generated/ \
	logs/**/*.diff \
	logs/**/*.json \
	logs/**/*.jsonl \
	tests/fixtures/workspace/bad.md \
	.tool-versions \
	TREE.txt


gen-gitignore-deps:
	@which ignr > /dev/null || (echo "Error: ignr not found. Run: brew tap byteowlz/tap && brew install ignr"; exit 1)

gen-tree-deps:
	@which fd > /dev/null || (echo "Error: fd not found. Run: brew install fd"; exit 1)
	@which tree > /dev/null || (echo "Error: tree not found. Run: brew install tree"; exit 1)


## Bootstrap a .gitignore (won't overwite existing).
gen/gitignore: gen-gitignore-deps
	@if [ ! -f .gitignore ]; then \
		echo "Bootstrapping .gitignore..."; \
		ignr generate --no-detect --add python --add macos --add vscode; \
		echo "" >> .gitignore; \
		echo "# === project ===" >> .gitignore; \
		for item in $(GEN_GITIGNORE_EXTRAS); do \
			echo "$$item" >> .gitignore; \
		done; \
		echo "Done."; \
	else \
		echo "Skip: .gitignore already exists."; \
	fi

## Write project tree to TREE.txt.
gen/tree: gen-tree-deps
	@echo "Writing project tree..."
	@fd | sort | tree --fromfile --dirsfirst --noreport -a -F -o TREE.txt
	@sed -i '' '1s|^\.|$(GEN_PROJECT_NAME)|' TREE.txt
