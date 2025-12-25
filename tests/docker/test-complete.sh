#!/bin/bash
# Comprehensive end-to-end test for all SCIP languages
# Phase 1: Test base environment (expect failures)
# Phase 2: Build language-specific environments
# Phase 3: Test complete environments (expect success)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
FIXTURES_DIR="$REPO_ROOT/tests/fixtures"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "=========================================="
echo "CICADA SCIP Language Complete E2E Tests"
echo "=========================================="
echo ""

# Build base images (native and amd64 for tools without ARM binaries)
echo -e "${BLUE}━━━ Building Base Images ━━━${NC}"
docker build -t cicada-base -f "$SCRIPT_DIR/Dockerfile.base" "$REPO_ROOT"
echo -e "${YELLOW}Building amd64 base image for tools without ARM binaries...${NC}"
docker build --platform linux/amd64 -t cicada-base:amd64 -f "$SCRIPT_DIR/Dockerfile.base" "$REPO_ROOT"
echo ""

# Language configurations
# Format: "name:fixture:dockerfile:image:platform"
# platform is optional - empty means native, "linux/amd64" forces x86_64 emulation
LANGUAGES=(
    "Go:sample_go:Dockerfile.go:cicada-go:"
    "Java:sample_java:Dockerfile.java:cicada-java:"
    "Scala:sample_scala:Dockerfile.scala:cicada-scala:"
    "Ruby:sample_ruby:Dockerfile.ruby:cicada-ruby:linux/amd64"
    "Dart:sample_dart:Dockerfile.dart:cicada-dart:linux/amd64"
    "C:sample_c:Dockerfile.c:cicada-c:linux/amd64"
    "C++:sample_cpp:Dockerfile.c:cicada-c:linux/amd64"
    "C#:sample_csharp:Dockerfile.dotnet:cicada-dotnet:"
    "VB:sample_vb:Dockerfile.dotnet:cicada-dotnet:"
)

# Track results
PHASE1_FAILED=0
PHASE1_TOTAL=0
PHASE3_PASSED=0
PHASE3_TOTAL=0

#############################################################
# PHASE 1: Test with base image (expect failures)
#############################################################
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}PHASE 1: Base Environment Tests${NC}"
echo -e "${BLUE}Expected: All languages fail with helpful errors${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

for lang_config in "${LANGUAGES[@]}"; do
    IFS=':' read -r lang_name fixture_name dockerfile image_name <<< "$lang_config"
    fixture_path="$FIXTURES_DIR/$fixture_name"

    PHASE1_TOTAL=$((PHASE1_TOTAL + 1))

    echo -e "${YELLOW}Testing: $lang_name (base environment)${NC}"

    if [ ! -d "$fixture_path" ]; then
        echo -e "${RED}  ❌ SKIP: Fixture not found${NC}"
        continue
    fi

    # Run and capture output
    docker run --rm \
        -v "$fixture_path:/workspace/project" \
        cicada-base \
        bash -c "cd /workspace/project && cicada claude --fast 2>&1 || true" \
        > /tmp/cicada-phase1-$fixture_name.log 2>&1

    # Check for expected failure with clear error
    if grep -q "Indexed.*files" /tmp/cicada-phase1-$fixture_name.log; then
        echo -e "${RED}  ❌ UNEXPECTED SUCCESS (should have failed!)${NC}"
    elif grep -qE "(not found|No such file|Install)" /tmp/cicada-phase1-$fixture_name.log; then
        error_msg=$(grep -m 1 -E "(not found|No such file|Install)" /tmp/cicada-phase1-$fixture_name.log | head -c 80)
        echo -e "${GREEN}  ✅ Failed as expected: ${error_msg}...${NC}"
        PHASE1_FAILED=$((PHASE1_FAILED + 1))
    else
        echo -e "${RED}  ❌ Failed without clear error message${NC}"
        echo "     Check log: /tmp/cicada-phase1-$fixture_name.log"
    fi
done

echo ""
echo -e "${GREEN}Phase 1 Summary: $PHASE1_FAILED/$PHASE1_TOTAL languages failed with clear errors${NC}"
echo ""

#############################################################
# PHASE 2: Build language-specific images
#############################################################
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}PHASE 2: Building Language-Specific Images${NC}"
echo -e "${BLUE}This caches SCIP tools for future runs${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Get unique dockerfiles, images, and platforms (bash 3.x compatible)
UNIQUE_BUILDS=""
for lang_config in "${LANGUAGES[@]}"; do
    IFS=':' read -r lang_name fixture_name dockerfile image_name platform <<< "$lang_config"
    build_entry="$dockerfile:$image_name:$platform"
    # Check if already in list
    if [[ ! "$UNIQUE_BUILDS" =~ "$build_entry" ]]; then
        UNIQUE_BUILDS="$UNIQUE_BUILDS $build_entry"
    fi
done

# Build each unique image
for build_entry in $UNIQUE_BUILDS; do
    IFS=':' read -r dockerfile image_name platform <<< "$build_entry"
    echo -e "${YELLOW}Building: $image_name${NC}"
    if [ -n "$platform" ]; then
        echo "  (using platform: $platform with amd64 base)"
        docker build --platform "$platform" --build-arg BASE_IMAGE=cicada-base:amd64 -t "$image_name" -f "$SCRIPT_DIR/$dockerfile" "$REPO_ROOT"
    else
        docker build -t "$image_name" -f "$SCRIPT_DIR/$dockerfile" "$REPO_ROOT"
    fi
    echo ""
done

echo -e "${GREEN}All language images built successfully!${NC}"
echo ""

#############################################################
# PHASE 3: Test with complete environments (expect success)
#############################################################
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}PHASE 3: Complete Environment Tests${NC}"
echo -e "${BLUE}Expected: All languages index successfully${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

for lang_config in "${LANGUAGES[@]}"; do
    IFS=':' read -r lang_name fixture_name dockerfile image_name platform <<< "$lang_config"
    fixture_path="$FIXTURES_DIR/$fixture_name"

    PHASE3_TOTAL=$((PHASE3_TOTAL + 1))

    echo -e "${YELLOW}Testing: $lang_name (complete environment)${NC}"

    if [ ! -d "$fixture_path" ]; then
        echo -e "${RED}  ❌ SKIP: Fixture not found${NC}"
        continue
    fi

    # Run and capture output (use platform flag if specified)
    if [ -n "$platform" ]; then
        docker run --rm --platform "$platform" \
            -v "$fixture_path:/workspace/project" \
            "$image_name" \
            bash -c "cd /workspace/project && cicada claude --fast 2>&1" \
            > /tmp/cicada-phase3-$fixture_name.log 2>&1
    else
        docker run --rm \
            -v "$fixture_path:/workspace/project" \
            "$image_name" \
            bash -c "cd /workspace/project && cicada claude --fast 2>&1" \
            > /tmp/cicada-phase3-$fixture_name.log 2>&1
    fi

    # Check for success
    if grep -q "Indexed.*files" /tmp/cicada-phase3-$fixture_name.log; then
        indexed_line=$(grep "Indexed.*files" /tmp/cicada-phase3-$fixture_name.log)
        echo -e "${GREEN}  ✅ SUCCESS: $indexed_line${NC}"
        PHASE3_PASSED=$((PHASE3_PASSED + 1))
    else
        echo -e "${RED}  ❌ FAILED${NC}"
        echo "     Last 10 lines:"
        tail -10 /tmp/cicada-phase3-$fixture_name.log | sed 's/^/     /'
        echo "     Full log: /tmp/cicada-phase3-$fixture_name.log"
    fi
done

echo ""
echo -e "${GREEN}Phase 3 Summary: $PHASE3_PASSED/$PHASE3_TOTAL languages indexed successfully${NC}"
echo ""

#############################################################
# FINAL SUMMARY
#############################################################
echo "=========================================="
echo "FINAL SUMMARY"
echo "=========================================="
echo ""
echo "Phase 1 (Base Environment - Expect Failures):"
echo "  $PHASE1_FAILED/$PHASE1_TOTAL languages failed with clear error messages"
echo ""
echo "Phase 3 (Complete Environment - Expect Success):"
echo "  $PHASE3_PASSED/$PHASE3_TOTAL languages indexed successfully"
echo ""

if [ "$PHASE1_FAILED" -eq "$PHASE1_TOTAL" ] && [ "$PHASE3_PASSED" -eq "$PHASE3_TOTAL" ]; then
    echo -e "${GREEN}✅ ALL TESTS PASSED!${NC}"
    echo "   - Base environment correctly shows missing dependencies"
    echo "   - Complete environments successfully index all languages"
    exit 0
else
    echo -e "${RED}❌ SOME TESTS FAILED${NC}"
    echo "   Review logs in /tmp/cicada-phase*.log"
    exit 1
fi
