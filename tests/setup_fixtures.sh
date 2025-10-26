#!/bin/bash
# Generate test fixture index before running tests

set -e

echo "Setting up test fixtures..."

# Generate index for test fixtures
if [ -d "tests/fixtures/elixir_project" ]; then
    echo "Generating index for tests/fixtures/elixir_project..."
    python -m cicada.indexer tests/fixtures/elixir_project --output tests/fixtures/.cicada/index.json
    echo "✓ Test fixtures generated successfully"
else
    echo "⚠ Warning: tests/fixtures/elixir_project not found"
    exit 1
fi
