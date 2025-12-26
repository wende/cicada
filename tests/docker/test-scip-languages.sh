#!/bin/bash
# Fast SCIP language tests using pre-built all-in-one image
#
# Tests two scenarios per language:
# 1. Without indexer (SCIP_ENABLE unset) - should fail gracefully
# 2. With indexer (SCIP_ENABLE=<lang>) - should succeed
#
# Usage:
#   ./test-scip-languages.sh          # Test all languages
#   ./test-scip-languages.sh go java  # Test specific languages

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
FIXTURES_DIR="$REPO_ROOT/tests/fixtures"
IMAGE_NAME="cicada-all-scip"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# All languages and their fixtures (bash 3.2 compatible)
ALL_LANGUAGES="go java scala ruby dart c cpp csharp vb"

get_fixture() {
    case "$1" in
        go) echo "sample_go" ;;
        java) echo "sample_java" ;;
        scala) echo "sample_scala" ;;
        ruby) echo "sample_ruby" ;;
        dart) echo "sample_dart" ;;
        c) echo "sample_c" ;;
        cpp) echo "sample_cpp" ;;
        csharp) echo "sample_csharp" ;;
        vb) echo "sample_vb" ;;
        *) echo "" ;;
    esac
}

# Results storage (files instead of associative arrays)
RESULTS_DIR=$(mktemp -d)
trap "rm -rf $RESULTS_DIR" EXIT

build_image() {
    echo -e "${BLUE}Building $IMAGE_NAME image...${NC}"
    echo "This may take a few minutes on first run..."
    echo ""
    docker build -t "$IMAGE_NAME" -f "$SCRIPT_DIR/Dockerfile.all-scip" "$REPO_ROOT"
    echo ""
}

test_language() {
    local lang=$1
    local fixture=$(get_fixture "$lang")
    local fixture_path="$FIXTURES_DIR/$fixture"

    if [ -z "$fixture" ] || [ ! -d "$fixture_path" ]; then
        echo -e "${YELLOW}SKIP: Fixture not found for $lang${NC}"
        echo "SKIP" > "$RESULTS_DIR/${lang}_no_deps"
        echo "SKIP" > "$RESULTS_DIR/${lang}_with_deps"
        return
    fi

    echo -e "${BLUE}━━━ Testing: $lang ━━━${NC}"

    # Test 1: Without indexer (should fail gracefully)
    echo -n "  Without deps: "
    local output_no_deps
    output_no_deps=$(docker run --rm \
        -v "$fixture_path:/workspace/project:ro" \
        -w /workspace/project \
        "$IMAGE_NAME" \
        cicada claude 2>&1) || true

    if echo "$output_no_deps" | grep -qi "not found\|install via"; then
        echo -e "${GREEN}✓ Graceful failure${NC}"
        echo "PASS" > "$RESULTS_DIR/${lang}_no_deps"
    else
        echo -e "${RED}✗ Unexpected behavior${NC}"
        echo "FAIL" > "$RESULTS_DIR/${lang}_no_deps"
        echo "    Output: $(echo "$output_no_deps" | head -3)"
    fi

    # Test 2: With indexer (should succeed)
    # Note: Not using :ro because SCIP indexers need to write index.scip to the project dir
    echo -n "  With deps:    "
    local output_with_deps
    output_with_deps=$(docker run --rm \
        -e "SCIP_ENABLE=$lang" \
        -v "$fixture_path:/workspace/project" \
        -w /workspace/project \
        "$IMAGE_NAME" \
        cicada claude 2>&1) || true

    if echo "$output_with_deps" | grep -qi "indexed.*file"; then
        local indexed_line=$(echo "$output_with_deps" | grep -i "indexed" | head -1)
        echo -e "${GREEN}✓ $indexed_line${NC}"
        echo "PASS" > "$RESULTS_DIR/${lang}_with_deps"
    else
        echo -e "${RED}✗ Failed to index${NC}"
        echo "FAIL" > "$RESULTS_DIR/${lang}_with_deps"
        echo "    Output: $(echo "$output_with_deps" | tail -5)"
    fi

    echo ""
}

print_summary() {
    echo -e "${BLUE}═══════════════════════════════════════════${NC}"
    echo -e "${BLUE}                  SUMMARY                   ${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════${NC}"
    printf "%-10s %-15s %-15s\n" "Language" "No Deps" "With Deps"
    echo "──────────────────────────────────────────"

    local all_pass=true
    for lang in $ALL_LANGUAGES; do
        local no_deps="N/A"
        local with_deps="N/A"

        [ -f "$RESULTS_DIR/${lang}_no_deps" ] && no_deps=$(cat "$RESULTS_DIR/${lang}_no_deps")
        [ -f "$RESULTS_DIR/${lang}_with_deps" ] && with_deps=$(cat "$RESULTS_DIR/${lang}_with_deps")

        # Color the results
        local no_deps_display="$no_deps"
        local with_deps_display="$with_deps"

        case "$no_deps" in
            PASS) no_deps_display="${GREEN}PASS${NC}" ;;
            FAIL) no_deps_display="${RED}FAIL${NC}"; all_pass=false ;;
            SKIP) no_deps_display="${YELLOW}SKIP${NC}" ;;
        esac

        case "$with_deps" in
            PASS) with_deps_display="${GREEN}PASS${NC}" ;;
            FAIL) with_deps_display="${RED}FAIL${NC}"; all_pass=false ;;
            SKIP) with_deps_display="${YELLOW}SKIP${NC}" ;;
        esac

        printf "%-10s $no_deps_display%*s$with_deps_display\n" "$lang" $((15 - ${#no_deps})) ""
    done

    echo ""
    if $all_pass; then
        echo -e "${GREEN}All tests passed!${NC}"
    else
        echo -e "${RED}Some tests failed.${NC}"
        return 1
    fi
}

# Main
echo "=========================================="
echo "CICADA SCIP Language Tests (Optimized)"
echo "=========================================="
echo ""

# Determine which languages to test
if [ $# -gt 0 ]; then
    LANGUAGES="$*"
else
    LANGUAGES="$ALL_LANGUAGES"
fi

# Build image once
build_image

# Run tests
for lang in $LANGUAGES; do
    if [ -z "$(get_fixture "$lang")" ]; then
        echo -e "${RED}Unknown language: $lang${NC}"
        continue
    fi
    test_language "$lang"
done

print_summary
