#!/bin/bash
# Usage: ./tests/acceptance/check_functiondoc.sh function_name
#
# Tests that:
# 1. Function @doc is displayed
# 2. Examples are extracted from @doc and shown separately

FUNCTION="${1:-resolve_all_types}"

uv run python tests/acceptance/runner.py search_function "$FUNCTION"
