#!/bin/bash
# Generate test fixture index before running tests

set -e

echo "Setting up test fixtures..."

# Determine which fixture to use (local dev vs CI)
if [ -d "tests/fixtures/elixir_project" ]; then
    FIXTURE_DIR="tests/fixtures/elixir_project"
    echo "Using local development fixture: elixir_project"
elif [ -d "tests/fixtures/test_project" ]; then
    FIXTURE_DIR="tests/fixtures/test_project"
    echo "Using existing test fixture: test_project"
else
    # Create minimal test fixture for CI
    echo "Creating minimal test fixture..."
    bash tests/create_test_fixture.sh
    FIXTURE_DIR="tests/fixtures/test_project"
fi

# Generate index for test fixtures
echo "Generating index for $FIXTURE_DIR..."
if command -v uv >/dev/null 2>&1; then
    uv run python -m cicada.indexer "$FIXTURE_DIR" --output tests/fixtures/.cicada/index.json
else
    python -m cicada.indexer "$FIXTURE_DIR" --output tests/fixtures/.cicada/index.json
fi
echo "✓ Test fixtures generated successfully"

# Create config.yaml for acceptance tests
echo "Creating config for test fixtures..."
mkdir -p tests/fixtures/.cicada
cat > tests/fixtures/.cicada/config.yaml << EOF
repository:
  path: $FIXTURE_DIR

storage:
  index_path: tests/fixtures/.cicada/index.json
EOF
echo "✓ Config created for test fixtures"
