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

# Get absolute path for fixture directory
FIXTURE_DIR_ABS=$(cd "$FIXTURE_DIR" && pwd)

# Generate index using cicada CLI (uses centralized storage automatically)
echo "Generating index for $FIXTURE_DIR..."
if command -v uv >/dev/null 2>&1; then
    uv run cicada index "$FIXTURE_DIR_ABS" --default
else
    cicada index "$FIXTURE_DIR_ABS" --default
fi
echo "✓ Test fixtures generated successfully"

# Generate TypeScript SCIP index if sample_typescript exists
if [ -d "tests/fixtures/sample_typescript" ]; then
    echo "Generating TypeScript SCIP index..."
    pushd tests/fixtures/sample_typescript > /dev/null

    # Install npm dependencies if needed
    if [ ! -d "node_modules" ]; then
        echo "Installing npm dependencies..."
        npm install
    fi

    # Generate SCIP index
    echo "Running scip-typescript indexer..."
    npx @sourcegraph/scip-typescript index

    # Verify index was created
    if [ -f "index.scip" ]; then
        echo "✓ TypeScript SCIP index generated successfully"
    else
        echo "✗ Failed to generate TypeScript SCIP index"
        popd > /dev/null
        exit 1
    fi

    popd > /dev/null
fi

# Create config.yaml for acceptance tests (now uses centralized storage)
echo "Creating config for test fixtures..."
# Get storage directory hash
if command -v uv >/dev/null 2>&1; then
    STORAGE_DIR=$(uv run python3 -c "
from pathlib import Path
from cicada.utils.storage import get_config_path
config_path = get_config_path('$FIXTURE_DIR_ABS')
print(config_path.parent)
")
else
    STORAGE_DIR=$(python3 -c "
from pathlib import Path
from cicada.utils.storage import get_config_path
config_path = get_config_path('$FIXTURE_DIR_ABS')
print(config_path.parent)
")
fi

# Config is already in centralized storage, just verify it exists
if [ -f "$STORAGE_DIR/config.yaml" ]; then
    echo "✓ Config already exists at $STORAGE_DIR/config.yaml"
else
    # Create it if it doesn't exist
    mkdir -p "$STORAGE_DIR"
    cat > "$STORAGE_DIR/config.yaml" << EOF
repository:
  path: $FIXTURE_DIR_ABS
EOF
    echo "✓ Config created at $STORAGE_DIR/config.yaml"
fi
