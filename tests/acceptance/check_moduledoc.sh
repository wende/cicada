#!/bin/bash
# Usage: ./tests/acceptance/check_moduledoc.sh ModuleName
#
# Tests that moduledoc is displayed when searching for modules

MODULE="${1:-AB.Generators}"

uv run python tests/acceptance/runner.py search_module "$MODULE"
