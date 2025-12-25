#!/bin/bash
# End-to-end test for all SCIP languages in clean Docker environment
# This script EXPECTS failures - it's designed to show what breaks

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
FIXTURES_DIR="$REPO_ROOT/tests/fixtures"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=========================================="
echo "CICADA SCIP Language E2E Tests"
echo "Testing in clean Docker environment"
echo "=========================================="
echo ""

# Build base image
echo "Building base Docker image..."
docker build -t cicada-base -f "$SCRIPT_DIR/Dockerfile.base" "$REPO_ROOT"
echo ""

test_language() {
    local lang_name=$1
    local fixture_name=$2
    local fixture_path="$FIXTURES_DIR/$fixture_name"

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Testing: $lang_name"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    if [ ! -d "$fixture_path" ]; then
        echo -e "${RED}❌ SKIP: Fixture not found at $fixture_path${NC}"
        echo ""
        return 1
    fi

    # Run test in Docker with live output
    echo "Running in clean Docker container..."
    echo ""

    # Save output to both terminal and file
    docker run --rm \
        -v "$fixture_path:/workspace/project:ro" \
        cicada-base \
        bash -c "
            cd /workspace/project && \
            cicada claude --fast 2>&1 || true
        " 2>&1 | tee /tmp/cicada-test-$fixture_name.log

    # Check results
    echo ""
    if grep -q "Indexed.*files" /tmp/cicada-test-$fixture_name.log; then
        indexed_line=$(grep "Indexed.*files" /tmp/cicada-test-$fixture_name.log)
        echo -e "${GREEN}✅ SUCCESS: $indexed_line${NC}"
    else
        echo -e "${RED}❌ FAILED - see output above${NC}"
        echo "Full log saved to: /tmp/cicada-test-$fixture_name.log"
    fi
}

# Test all languages
test_language "Go" "sample_go"
test_language "Java" "sample_java"
test_language "Scala" "sample_scala"
test_language "Ruby" "sample_ruby"
test_language "Dart" "sample_dart"
test_language "C" "sample_c"
test_language "C++" "sample_cpp"
test_language "C#" "sample_csharp"
test_language "VB" "sample_vb"

echo "=========================================="
echo "Testing Complete"
echo "=========================================="
echo ""
echo "Review full logs in /tmp/cicada-test-*.log"
