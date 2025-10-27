#!/bin/bash
# Usage: ./tests/acceptance/test_keyword_extraction.sh [--small] [--medium] [--large] [text]
# Tests keyword extraction with specified spaCy models
#
# Options:
#   --small   Test with small model (en_core_web_sm) - default if no flags specified
#   --medium  Test with medium model (en_core_web_md)
#   --large   Test with large model (en_core_web_lg)
#
# Examples:
#   ./tests/acceptance/test_keyword_extraction.sh
#   ./tests/acceptance/test_keyword_extraction.sh --small --medium
#   ./tests/acceptance/test_keyword_extraction.sh --large "Custom text to analyze"
#   ./tests/acceptance/test_keyword_extraction.sh --small --medium --large

# Default test text
DEFAULT_TEXT="This function validates user authentication and handles HTTP requests. It uses camelCase naming like getUserData and snake_case like get_user_info. The module implements type checking with TypeScript and performs database queries using PostgreSQL."

# Parse arguments
TEST_SMALL=false
TEST_MEDIUM=false
TEST_LARGE=false
CUSTOM_TEXT=""

for arg in "$@"; do
    case $arg in
        --small)
            TEST_SMALL=true
            shift
            ;;
        --medium)
            TEST_MEDIUM=true
            shift
            ;;
        --large)
            TEST_LARGE=true
            shift
            ;;
        *)
            # Remaining argument is custom text
            if [ -n "$arg" ]; then
                CUSTOM_TEXT="$arg"
            fi
            shift
            ;;
    esac
done

# If no model flags specified, default to small only
if [ "$TEST_SMALL" = false ] && [ "$TEST_MEDIUM" = false ] && [ "$TEST_LARGE" = false ]; then
    TEST_SMALL=true
fi

# Use custom text or default
TEXT="${CUSTOM_TEXT:-$DEFAULT_TEXT}"

# Function to test a model
test_model() {
    local MODEL_SIZE=$1
    local MODEL_NAME=$2
    local MODEL_NUMBER=$3

    echo "${MODEL_NUMBER}. ${MODEL_NAME} MODEL (en_core_web_${MODEL_SIZE})"
    echo "--------------------------------"

    uv run python -c "
from cicada.keyword_extractor import KeywordExtractor
import sys

try:
    extractor = KeywordExtractor(verbose=False, model_size='${MODEL_SIZE}')
    text = '''${TEXT}'''
    result = extractor.extract_keywords(text, top_n=10)

    print('Top Keywords:')
    for keyword, count in result['top_keywords']:
        print(f'  - {keyword} ({count} occurrences)')

    print(f\"\\nStats: {result['stats']['total_tokens']} tokens, {result['stats']['sentences']} sentences\")
    print(f\"Nouns: {', '.join(result['nouns'][:10])}\")
    print(f\"Verbs: {', '.join(result['verbs'][:10])}\")
    if result['code_identifiers']:
        print(f\"Code identifiers: {', '.join(result['code_identifiers'])}\")
    if result['code_split_words']:
        print(f\"Code split words: {', '.join(sorted(result['code_split_words']))}\")
    if result['entities']:
        print(f\"Entities: {', '.join([f'{ent[0]} ({ent[1]})' for ent in result['entities']])}\")

    sys.exit(0)
except Exception as e:
    print(f'Error: {e}', file=sys.stderr)
    sys.exit(1)
"

    if [ $? -ne 0 ]; then
        echo "❌ Failed to extract keywords with ${MODEL_SIZE} model"
        return 1
    fi

    echo ""
}

echo "Testing keyword extraction"
echo "=============================================="
echo ""
echo "Input text:"
echo "\"$TEXT\""
echo ""
echo "=============================================="
echo ""

MODEL_COUNT=1

# Test requested models
if [ "$TEST_SMALL" = true ]; then
    test_model "small" "SMALL" "$MODEL_COUNT"
    MODEL_COUNT=$((MODEL_COUNT + 1))
    if [ "$TEST_MEDIUM" = true ] || [ "$TEST_LARGE" = true ]; then
        echo "=============================================="
        echo ""
    fi
fi

if [ "$TEST_MEDIUM" = true ]; then
    test_model "medium" "MEDIUM" "$MODEL_COUNT"
    MODEL_COUNT=$((MODEL_COUNT + 1))
    if [ "$TEST_LARGE" = true ]; then
        echo "=============================================="
        echo ""
    fi
fi

if [ "$TEST_LARGE" = true ]; then
    test_model "large" "LARGE" "$MODEL_COUNT"
fi

echo "=============================================="
echo ""
echo "✓ Test completed successfully!"
echo ""
echo "Note: Different model sizes may extract slightly different keywords."
echo "Larger models are more accurate but slower and use more memory."
