################################################################################
# tasks/json.make (json)
# Tasks related to json.
################################################################################
.PHONY: json/fmt json/tidy

json-dprint-deps:
	@which dprint > /dev/null || (echo "Error: dprint not found"; exit 1)

## Format all json files.
json/fmt: json-dprint-deps
	@echo "Formatting all json files..."
	@dprint fmt --config dprint.json "**/*.{json,jsonc}"

## Tidy all json files.
json/tidy: json/fmt
	@echo "Tidied all json files."