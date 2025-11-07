#!/bin/bash
# Usage: ./tests/acceptance/search_by_features.sh keyword1 keyword2 keyword3
# Example: ./tests/acceptance/search_by_features.sh performance benchmark test
# Example: ./tests/acceptance/search_by_features.sh create* test_*
#
# Author: Cursor(Auto)

# Check if keywords were provided
if [ $# -eq 0 ]; then
    echo "Usage: $0 keyword1 [keyword2] [keyword3] ..."
    echo "Example: $0 performance benchmark test"
    echo "Example: $0 create* test_*"
    exit 1
fi

echo "Searching for keywords: $@"
echo "========================================"
echo ""

uv run python tests/acceptance/runner.py search_keywords "$@"
