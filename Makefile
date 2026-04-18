################################################################################
# Makefile
# The orchestrator makefile.
################################################################################

################################################################################
# HELP (default)
# Automatically generate well-formatted output for any target that has a "##"
# comment preceding it.
################################################################################
.PHONY: help check-all

default: help

help:
	@printf "Available targets:\n\n"
	@awk '/^[a-zA-Z\-_0-9%:\\]+/ { \
		helpMessage = match(lastLine, /^## (.*)/); \
		if (helpMessage) { \
			helpCommand = $$1; \
			helpMessage = substr(lastLine, RSTART + 3, RLENGTH); \
			gsub("\\\\", "", helpCommand); \
			gsub(":+$$", "", helpCommand); \
			printf "  \x1b[32;01m%-35s\x1b[0m %s\n", helpCommand, helpMessage; \
		} \
	} \
	{ lastLine = $$0 }' $(MAKEFILE_LIST) | sort -u
	@printf "\n"

################################################################################
# INCLUDES
# Avoid sticking every target in the same Makefile for the same reason we don't
# stick all code in the same source file.
################################################################################

-include tasks/*.make

.PHONY: keep/check keep/tidy

## Check all.
keep/check: md/lint yaml/lint py/lint py/security py/test
	@echo "All files checked."

## Tidy all.
keep/tidy: json/tidy md/tidy py/tidy toml/tidy yaml/tidy
	@echo "All files tidied."
