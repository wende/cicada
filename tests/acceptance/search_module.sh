#!/bin/bash
# Usage: ./tests/acceptance/search_module.sh ModuleName

MODULE="${1:-AB.Generators}"

uv run python tests/acceptance/runner.py search_module "$MODULE"
